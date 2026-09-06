"""Test de connexion LLM — ping fail-fast de tous les modèles configurés (v6 §4).

Usage : python scripts/tester_llm.py
Lit la configuration dans .env (base_url, clé, modèle par phase).
Sortie : PING_OK/PING_KO par phase + gabarit du message fail-fast si indisponible.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings  # noqa: E402
from app.llm.client import ClientLLM  # noqa: E402

PHASES = [
    ("phase2", settings.modele_phase2),
    ("forme", settings.modele_forme),
    ("style", settings.modele_style),
    ("technique", settings.modele_technique),
    ("embellissement", settings.modele_embellissement),
]


async def main() -> int:
    client = ClientLLM()
    print(f"Fournisseur : {settings.llm_base_url}")
    print(f"Modèle par phase : {[m for _, m in PHASES]}\n")
    code_sortie = 0
    for nom_phase, modele in PHASES:
        if not modele:
            print(f"[{nom_phase}] NON CONFIGURÉ")
            code_sortie = 1
            continue
        ok = await client.ping(modele)
        print(f"[{nom_phase}] {'PING_OK' if ok else 'PING_KO'} ({modele})")
        if not ok:
            print(
                f"  ⛔ Exécution interrompue — la phase {nom_phase} ne répond pas.\n"
                "  Aucune donnée narrative n'a été écrite. "
                "Vérifiez APP_LLM_BASE_URL / APP_LLM_API_KEY et renvoyez votre texte."
            )
            code_sortie = 1
    return code_sortie


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
