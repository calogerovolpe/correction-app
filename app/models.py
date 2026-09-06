"""Schémas Pydantic — contrats LLM stricts et modèles internes (v6 §8.2, §8.5).

Le champ `groupe` est absent du contrat LLM (décision v6) : les identifiants
de bloc `g-XXXX` sont calculés par Python au rendu (Phase 7).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Phase = Literal["forme", "style", "technique", "embellissement"]


class PannePhase(Exception):
    """Panne d'une phase en cours d'analyse (v6 §8.5) : JSON non parsable ou racine
    non conforme au schéma. Déclenche l'Option B (v6 §14.2).

    IMPORTANT : une liste valide vide n'est JAMAIS une panne (texte sans faute,
    aucune incohérence détectée) — c'est un résultat normal.
    """

    def __init__(self, phase: str, cause: str):
        super().__init__(f"Phase {phase} : {cause}")
        self.phase = phase
        self.cause = cause


class Correction(BaseModel):
    """Contrat JSON d'une correction LLM (v6 §8.2), `extra='forbid'` strict (v6 §8.5)."""
    model_config = ConfigDict(extra="forbid")

    id: str
    phase: Phase
    type: str
    paragraphe_id: str = Field(pattern=r"^p-\d+$")
    debut: int = Field(ge=0)
    fin: int = Field(gt=0)
    contexte_avant: str = ""
    original: str
    correction: str
    explication: str
    regle: str = ""
    variantes: list[str] = []


class EmbellissementMigre(BaseModel):
    """Suggestion d'Embellissement migrée dans le tooltip d'une correction Style (v6 §8.4)."""
    suggestion: str
    variantes: list[str]
    explication: str


class CorrectionFusionnee(BaseModel):
    """Résultat de la déduplication : une correction hôte + l'embellissement éventuellement migré."""
    correction: Correction
    embellissement_migre: EmbellissementMigre | None = None


class AlerteDetectee(BaseModel):
    """Incohérence narrative détectée par la Phase 2 (v6 §6.7)."""
    model_config = ConfigDict(extra="forbid")

    code: str
    niveau: Literal["avertissement", "information"]
    cible: str = ""
    motif: str


class ReponseAlertes(BaseModel):
    """Racine attendue de la Phase 2 (v6 §8.5) : {"alertes": [...]}, liste vide valide."""
    model_config = ConfigDict(extra="forbid")

    alertes: list[AlerteDetectee]


class DeltaRelecture(BaseModel):
    """Delta produit par la relecture-diff du remplacement officiel (v6 §6.6)."""
    model_config = ConfigDict(extra="forbid")

    fiche: str
    champ: str
    ancienne_valeur: str
    nouvelle_valeur: str


class ReponseDeltas(BaseModel):
    """Racine attendue de la relecture-diff (v6 §6.6) : {"deltas": [...]}, liste vide valide."""
    model_config = ConfigDict(extra="forbid")

    deltas: list[DeltaRelecture]
