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

# --- Modèles du texte riche (J2.2) ---

class RunFormat(BaseModel):
    """Segment de texte avec attributs de mise en forme Word (gras, italique, souligné)."""
    texte: str
    gras: bool = False
    italique: bool = False
    souligne: bool = False


class ParagrapheRiche(BaseModel):
    """Paragraphe au format riche (un paragraphe Word = un bloc de runs)."""
    id: str = Field(pattern=r"^p-\d+$")
    runs: list[RunFormat] = []


class DemandeAlternatives(BaseModel):
    """Requête de l'utilisateur pour demander des alternatives ciblées à l'IA."""
    fragment: str
    paragraphe_texte: str
    phase: Literal["style", "embellissement"] = "style"
    mots_a_eviter: list[str] = []


class ReponseAlternatives(BaseModel):
    """Alternatives générées par le LLM."""
    model_config = ConfigDict(extra="forbid")
    alternatives: list[str] = []
    explication: str = ""


class ReponseEmbellissement(BaseModel):
    """Réécriture embellie d'un passage sélectionné (J2.5, à la demande)."""
    model_config = ConfigDict(extra="forbid")
    texte: str
    explication: str = ""

