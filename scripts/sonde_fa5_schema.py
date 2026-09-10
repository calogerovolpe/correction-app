"""Sonde FA5 — vérifie en DIRECT que le JSON Schema strict généré depuis le
contrat Pydantic `ReponseCorrections` est accepté par l'API Mistral.

Usage : .venv\\Scripts\\python scripts\\sonde_fa5_schema.py
(Ne fait partie ni de la suite pytest ni du produit — outil de vérification du jalon.)
"""

import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm.client import format_schema_strict  # noqa: E402
from app.llm.prompts import CONSIGNES_PHASES, prompt_phase_correction  # noqa: E402
from app.models import ReponseCorrections  # noqa: E402
from app.services.normalisation import Paragraphe  # noqa: E402


async def main() -> int:
    load_dotenv()
    cle = os.environ.get("APP_LLM_API_KEY")
    if not cle:
        print("APP_LLM_API_KEY absente")
        return 1
    paragraphes = [Paragraphe(id="p-1", texte="Les sentinelles monte la garde sur les remparts.")]
    messages = prompt_phase_correction("forme", CONSIGNES_PHASES["forme"], paragraphes, "france")
    import httpx  # noqa: F811

    async with httpx.AsyncClient(timeout=90) as client:
        reponse = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {cle}", "Content-Type": "application/json"},
            json={
                "model": "mistral-small-latest",
                "messages": messages,
                "temperature": 0.0,
                "max_tokens": 2048,
                "response_format": format_schema_strict(ReponseCorrections),
            },
        )
    print("statut :", reponse.status_code)
    if reponse.status_code != 200:
        print(reponse.text[:800])
        return 1
    choix = reponse.json()["choices"][0]
    print("finish_reason :", choix["finish_reason"])
    contenu = json.loads(choix["message"]["content"])
    validees = [ReponseCorrections.model_validate(contenu)]
    print("corrections validées par le contrat Pydantic :", len(validees[0].corrections))
    for c in validees[0].corrections:
        print("-", c.type, "|", c.original, "->", c.correction)
    return 0


if __name__ == "__main__":
    import json

    raise SystemExit(asyncio.run(main()))