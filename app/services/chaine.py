"""Gestion de la chaîne séquentielle déclarative et numéro attendu (J2.3).

L'utilisateur déclare le numéro et la catégorie. Python respecte son choix.
`numero_attendu` permet le pré-remplissage dans le formulaire.
"""

from dataclasses import dataclass
from typing import Literal

Decision = Literal[
    "chapitre",
    "passage",
    "extrait",
]


@dataclass(frozen=True)
class Arbitrage:
    """Résultat du choix déclaratif de l'utilisateur."""
    decision: str
    categorie: str
    numero: float | None = None
    message: str | None = None


def numero_attendu(projet: dict) -> float:
    """Numéro attendu par défaut :
    - Si projet vierge (courant is None) : 0 (Prologue)
    - Sinon : courant + 1
    """
    courant = projet.get("current_chapter_num")
    if courant is None:
        return 0.0
    return float(courant) + 1.0

