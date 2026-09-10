"""Schémas Pydantic — contrats LLM stricts et modèles internes (v6 §8.2, §8.5).

Le champ `groupe` est absent du contrat LLM (décision v6) : les identifiants
de bloc `g-XXXX` sont calculés par Python au rendu (Phase 7).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class ErreurTroncatureLLM(RuntimeError):
    """Le modèle a atteint la limite de tokens de sortie (`finish_reason='length'`,
    FA5) : la réponse est TRONQUÉE et inexploitable (JSON incomplet) — ne jamais
    l'ingérer. Convertie en `PannePhase` par le pipeline d'analyse (Option B) ;
    portée aussi par le `MockLLM` pour les tests."""


class Correction(BaseModel):
    """Contrat JSON d'une correction LLM (v6 §8.2), `extra='forbid'` strict (v6 §8.5).

    Invariants métier durcis (FA5) :
    - `fin > debut` strict (bornes inclusif/exclusif cohérentes) ;
    - `type`, `original` et `explication` ne peuvent pas être vides (une correction
      sans fragment identifié ni explication pédagogique n'a aucun sens pour
      l'auteur) — la cohérence fine `paragraphe[debut:fin] == original` reste
      validée/réparée par `reconciliation.reconcilier` (ancre, occurrence unique)
      et non ici : un durcissement prématuré empêcherait les réparations d'offsets.
    """
    model_config = ConfigDict(extra="forbid")

    id: str
    phase: Phase
    type: str = Field(min_length=1)
    paragraphe_id: str = Field(pattern=r"^p-\d+$")
    debut: int = Field(ge=0)
    fin: int = Field(gt=0)
    contexte_avant: str = ""
    original: str = Field(min_length=1)
    correction: str
    explication: str = Field(min_length=1)
    regle: str = ""
    variantes: list[str] = []

    @model_validator(mode="after")
    def _bornes_coherentes(self) -> "Correction":
        if self.fin <= self.debut:
            raise ValueError("fin doit être strictement supérieure à debut")
        return self


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


class ReponseCorrections(BaseModel):
    """Racine attendue des phases de correction (v6 §8.2) : {"corrections": [...]}.

    Sert de schéma STRICT pour les Custom Structured Outputs Mistral (FA5) :
    `response_format={"type": "json_schema", "json_schema": {"strict": True, ...}}`
    — le LLM ne peut plus émettre un JSON hors contrat. La validation fine
    (invariants par correction, réconciliation des offsets) reste dans
    `reconciliation.py` : rejet INDIVIDUEL sans arrêt du pipeline conservé.
    Une liste vide est un résultat valide (texte sans faute)."""
    model_config = ConfigDict(extra="forbid")

    corrections: list[Correction]


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

