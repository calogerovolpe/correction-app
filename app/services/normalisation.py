"""Normalisation des entrées — v6 §8.1 et §5.2.

Le texte normalisé est la base IMMUABLE analysée par toutes les phases (v6 §8.1) :
    retrait des commandes -> normalisation -> découpage -> offsets.
Conventions : paragraphes découpés sur lignes vides, numérotés base 1 (`p-1`, `p-2`…) ;
offsets = tranches Python (`debut` inclusif, `fin` exclusif) sur le paragraphe normalisé.
"""

import re
from dataclasses import dataclass

BOM = "﻿"

# Titre de chapitre sur la PREMIÈRE ligne uniquement (v6 §5.2) :
# regex numérique, ou mot exact « Prologue » (numéro 0) reconnu dans tous les cas.
REGEX_TITRE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*:\s*(\S.*)$")


class TexteTropLong(Exception):
    """Garde-fou anti-troncature silencieuse (v6 §2.3) : refus explicite au-delà de `max_caracteres`."""

    def __init__(self, longueur: int, maximum: int):
        super().__init__(
            f"Texte de {longueur} caractères — la limite est de {maximum}. "
            "Refus explicite, aucune troncature silencieuse du contexte."
        )
        self.longueur = longueur
        self.maximum = maximum


@dataclass(frozen=True)
class Paragraphe:
    """Un paragraphe normalisé, identifié `p-N` en base 1 (v6 §8.1)."""
    id: str
    texte: str


def normaliser(texte: str) -> str:
    """Normalisation stricte (v6 §8.1) : BOM supprimé, `\\r\\n`/`\\r` -> `\\n`,
    espaces de fin de ligne supprimés. Aucune autre transformation (pas de NFC) —
    fidélité au texte de l'auteur."""
    texte = texte.replace(BOM, "")
    texte = texte.replace("\r\n", "\n").replace("\r", "\n")
    lignes = [ligne.rstrip() for ligne in texte.split("\n")]
    return "\n".join(lignes)


def decouper_paragraphes(texte_normalise: str) -> list[Paragraphe]:
    """Découpage sur une ou plusieurs lignes vides (`\\n{2,}`), numérotation base 1.

    Les sauts de ligne simples restent au sein d'un même paragraphe : des répliques
    de dialogue non séparées par une ligne vide appartiennent au même paragraphe (v6 §8.1)."""
    blocs = [bloc for bloc in re.split(r"\n{2,}", texte_normalise) if bloc.strip()]
    return [Paragraphe(id=f"p-{i}", texte=bloc) for i, bloc in enumerate(blocs, start=1)]


def extraire_titre_chapitre(texte: str) -> tuple[float, str] | None:
    """Détecte un titre de chapitre sur la PREMIÈRE ligne uniquement (v6 §5.2).

    Retourne (numero, titre) — numéro 0 pour « Prologue » — ou None.
    Règle absolue : toute autre occurrence de cette structure numérique
    ailleurs dans le texte n'est JAMAIS considérée comme un titre."""
    premiere_ligne = texte.split("\n", 1)[0]
    correspondance = REGEX_TITRE.match(premiere_ligne)
    if correspondance:
        return float(correspondance.group(1)), correspondance.group(2).strip()
    if premiere_ligne.strip() == "Prologue":
        return 0.0, "Prologue"
    return None


def detecter_categorie(texte_normalise: str) -> str:
    """Catégorisation provisoire (v6 §5.2) : Chapitre (tout titre valide en première
    ligne, quel que soit le nombre de paragraphes), Passage (>= 3 paragraphes sans
    titre), Extrait (défaut). L'arbitrage final appartient à la machine d'états (§6.5)."""
    if extraire_titre_chapitre(texte_normalise) is not None:
        return "chapitre"
    if len(decouper_paragraphes(texte_normalise)) >= 3:
        return "passage"
    return "extrait"


def verifier_taille(texte: str, max_caracteres: int) -> None:
    """Garde-fou `max_caracteres` (v6 §2.3) : vérifié dès la Phase 1, refus explicite."""
    if len(texte) > max_caracteres:
        raise TexteTropLong(len(texte), max_caracteres)
