"""Client LLM compatible OpenAI (cahier des charges §4.3 / A4) — `/v1/chat/completions`.

Fournisseur unique : **Mistral par clé API** (décision A4) ; le client reste
compatible OpenAI, un changement de fournisseur resterait possible par
configuration seule. Le ping fail-fast (v6 §4.2) consomme `max_tokens=5` et
retente `retries_ping` NOUVELLES tentatives (1 -> 2 pings max par modèle).

FA5 — Robustesse LLM :
- Custom Structured Outputs : `schema_modele` (Pydantic) est traduit en
  `response_format={"type": "json_schema", "json_schema": {..., "strict": True}}`
  (supporté nativement par l'API Mistral) ;
- `verifier_troncature=True` : le `finish_reason` est inspecté systématiquement ;
  `"length"` lève `ErreurTroncatureLLM` (réponse tronquée = anomalie critique,
  jamais ingérée) — le ping et les appels Legacy restent inchangés."""

import asyncio
import logging
from typing import Any

import httpx
from pydantic import BaseModel

from app.config import settings
from app.models import ErreurTroncatureLLM

JOURNAL = logging.getLogger("correction.llm")


def format_schema_strict(schema_modele: type[BaseModel]) -> dict[str, Any]:
    """Traduit un modèle Pydantic en `response_format` Custom Structured Output
    Mistral (FA5) : {"type": "json_schema", "json_schema": {"name", "strict", "schema"}}."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_modele.__name__,
            "strict": True,
            "schema": schema_modele.model_json_schema(),
        },
    }


class ClientLLM:
    """Client minimal compatible OpenAI — pas de streaming, timeout strict (v6 §2.3)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        """`transport` injectable pour les tests (httpx.MockTransport)."""
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.llm_api_key
        self._transport = transport

    def _entetes(self) -> dict[str, str]:
        entetes = {"Content-Type": "application/json"}
        if self.api_key:
            entetes["Authorization"] = f"Bearer {self.api_key}"
        return entetes

    async def completer(
        self,
        modele: str,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        timeout: float | None = None,
        max_tokens: int | None = None,
        schema_modele: type[BaseModel] | None = None,
        verifier_troncature: bool = False,
    ) -> str:
        """Complétion non-stream (v6 §2.3) ; retourne le contenu du message.

        FA5 : `schema_modele` active les Custom Structured Outputs (json_schema
        strict généré depuis le contrat Pydantic) et `verifier_troncature=True`
        inspecte le `finish_reason` — `"length"` lève `ErreurTroncatureLLM`
        (JSON tronqué inexploitable) au lieu d'une erreur de syntaxe générique.
        Le ping (`max_tokens=5`) n'active PAS la vérification : sa réponse est
        volontairement coupée."""
        corps: dict[str, Any] = {
            "model": modele,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
        }
        if max_tokens is not None:
            corps["max_tokens"] = max_tokens
        if schema_modele is not None:
            corps["response_format"] = format_schema_strict(schema_modele)
        async with httpx.AsyncClient(
            timeout=timeout or settings.timeout_phase, transport=self._transport
        ) as client:
            reponse = await client.post(
                f"{self.base_url}/chat/completions", json=corps, headers=self._entetes()
            )
            reponse.raise_for_status()
            donnees = reponse.json()
        choix = donnees["choices"][0]
        if verifier_troncature and choix.get("finish_reason") == "length":
            raise ErreurTroncatureLLM(
                "Réponse tronquée : le modèle a atteint la limite de tokens de sortie "
                f"(finish_reason='length', max_tokens={max_tokens}). Le JSON est "
                "incomplet — l'appel est rejeté plutôt qu'ingéré (FA5)."
            )
        return choix["message"]["content"]

    async def ping(
        self, modele: str, timeout: float | None = None, retries: int | None = None
    ) -> bool:
        """Ping fail-fast (v6 §4.2) : `max_tokens=5`, `retries` nouvelles tentatives."""
        for tentative in range((retries if retries is not None else settings.retries_ping) + 1):
            try:
                await self.completer(
                    modele,
                    [{"role": "user", "content": "ping"}],
                    temperature=0.0,
                    timeout=timeout or settings.timeout_ping,
                    max_tokens=5,
                )
                return True
            except Exception as erreur:  # noqa: BLE001 — le ping doit avaler toutes les pannes
                JOURNAL.debug(
                    "Ping %s échoué (tentative %d) : %s", modele, tentative + 1, erreur
                )
        return False

    async def verifier_disponibilite(self, modeles: dict[str, str]) -> list[str]:
        """Fail-fast parallèle (v6 §4.2) : `{nom_phase: modèle}` -> phases indisponibles.
        Un ping réussi n'est pas une garantie de l'analyse — mais un échec évite
        de consommer le moindre token d'analyse."""
        resultats = await asyncio.gather(
            *(self.ping(modele) for modele in modeles.values())
        )
        return [nom for (nom, ok) in zip(modeles.keys(), resultats) if not ok]
