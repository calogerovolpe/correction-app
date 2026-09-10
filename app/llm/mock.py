"""Mock LLM (cahier des charges §9, jalon J1) : réponses scriptées par modèle,
injection de pannes, même interface que ClientLLM (ping, completer,
verifier_disponibilite) — déterministe et à coût nul pour les tests.

FA5 : le mock supporte les nouveaux paramètres du client (`schema_modele`,
`verifier_troncature`, `max_tokens`) et simule la TRONCATURE par budget de
sortie (`troncature=True` -> `ErreurTroncatureLLM`, comme un `finish_reason='length'`
réel)."""

import asyncio

from app.models import ErreurTroncatureLLM


class MockLLM:
    """Faux fournisseur compatible OpenAI pour les tests d'intégration.

    - `reponses` : {modèle: réponse scriptée} ; tout modèle absent répond
      par une liste vide valide : {\"corrections\": []} ;
    - `ping_ok=False` : simule l'indisponibilité au fail-fast ;
    - `panne_completer=True` : simule une panne EN COURS d'analyse
      (timeout/connexion) -> l'exception remonte et déclenche l'Option B ;
    - `troncature=True` (FA5) : simule un `finish_reason='length'` —
      `ErreurTroncatureLLM` est levée à l'appel (réponse tronquée) ;
    - `appels` : journal des appels pour assertions."""

    def __init__(
        self,
        reponses: dict[str, str] | None = None,
        ping_ok: bool = True,
        panne_completer: bool = False,
        troncature: bool = False,
    ):
        self.reponses = reponses or {}
        self.ping_ok = ping_ok
        self.panne_completer = panne_completer
        self.troncature = troncature
        self.appels: list[tuple[str, float]] = []

    async def ping(self, modele: str, timeout: float | None = None, retries: int | None = None) -> bool:
        return self.ping_ok

    async def completer(
        self,
        modele: str,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        timeout: float | None = None,
        max_tokens: int | None = None,
        schema_modele=None,
        verifier_troncature: bool = False,
    ) -> str:
        self.appels.append((modele, temperature))
        if self.panne_completer:
            raise RuntimeError("Panne simulée du fournisseur LLM (timeout/connexion)")
        if self.troncature:
            # Simule un finish_reason='length' : le JSON arrive coupé, l'appel
            # qui vérifie la troncature doit lever (FA5).
            raise ErreurTroncatureLLM(
                f"Réponse tronquée simulée (finish_reason='length', max_tokens={max_tokens})"
            )
        return self.reponses.get(modele, '{"corrections": []}')

    async def verifier_disponibilite(self, modeles: dict[str, str]) -> list[str]:
        if self.ping_ok:
            return []
        return list(modeles.keys())