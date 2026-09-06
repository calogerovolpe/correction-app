"""Mock LLM (cahier des charges §9, jalon J1) : réponses scriptées par modèle,
injection de pannes, même interface que ClientLLM (ping, completer,
verifier_disponibilite) — déterministe et à coût nul pour les tests."""

import asyncio


class MockLLM:
    """Faux fournisseur compatible OpenAI pour les tests d'intégration.

    - `reponses` : {modèle: réponse scriptée} ; tout modèle absent répond
      par une liste vide valide : {\"corrections\": []} ;
    - `ping_ok=False` : simule l'indisponibilité au fail-fast ;
    - `panne_completer=True` : simule une panne EN COURS d'analyse
      (timeout/connexion) -> l'exception remonte et déclenche l'Option B ;
    - `appels` : journal des appels pour assertions."""

    def __init__(
        self,
        reponses: dict[str, str] | None = None,
        ping_ok: bool = True,
        panne_completer: bool = False,
    ):
        self.reponses = reponses or {}
        self.ping_ok = ping_ok
        self.panne_completer = panne_completer
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
    ) -> str:
        self.appels.append((modele, temperature))
        if self.panne_completer:
            raise RuntimeError("Panne simulée du fournisseur LLM (timeout/connexion)")
        return self.reponses.get(modele, '{"corrections": []}')

    async def verifier_disponibilite(self, modeles: dict[str, str]) -> list[str]:
        if self.ping_ok:
            return []
        return list(modeles.keys())