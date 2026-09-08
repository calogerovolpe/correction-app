"""Réconciliation des offsets et déduplication Style/Embellissement — v6 §8.3, §8.4, §8.5.

Règles appliquées :
- Nettoyage des fences ```json et préambules avant tout parsing (v6 §8.5) ;
- Validation Pydantic `extra='forbid'` : rejet INDIVIDUEL sans arrêt du pipeline (v6 §8.5) ;
- Panne de phase = JSON non parsable ou racine non conforme (v6 §8.5). Une liste
  valide vide n'est JAMAIS une panne ;
- Réconciliation des offsets avec ancre `contexte_avant` (v6 §8.3) ;
- Déduplication = règle d'AFFICHAGE (R1-b) : AUCUNE correction n'est absorbée —
  en cas de recouvrement (exact ou partiel), Style et Embellissement coexistent
  (superposés dans la vue « Tout », séparés dans leurs onglets).
"""

import json
import logging
import re

from pydantic import ValidationError

from app.models import Correction, PannePhase
from app.services.normalisation import Paragraphe

JOURNAL = logging.getLogger("correction.reconciliation")


def nettoyer_sortie_llm(sortie: str) -> str:
    """Retire les fences ```json et préambules textuels ajoutés par le modèle (v6 §8.5)."""
    s = sortie.strip()
    correspondance = re.search(r"```(?:json)?\s*(.*?)```", s, re.DOTALL)
    if correspondance:
        s = correspondance.group(1).strip()
    positions = [p for p in (s.find("{"), s.find("[")) if p != -1]
    if positions:
        debut = min(positions)
        if debut > 0:
            s = s[debut:]
    return s


def extraire_corrections(sortie_llm: str, phase: str) -> list[Correction]:
    """Nettoie, parse et valide la sortie d'une phase de correction (v6 §8.5).

    Lève PannePhase si la sortie est non parsable ou si la racine est non conforme.
    Rejette individuellement les entrées invalides, sans arrêter le pipeline.
    Une liste valide vide est un résultat normal (texte sans faute)."""
    brut = nettoyer_sortie_llm(sortie_llm)
    try:
        donnees = json.loads(brut)
    except json.JSONDecodeError as erreur:
        raise PannePhase(phase, f"JSON non parsable : {erreur}") from erreur
    if not isinstance(donnees, dict) or not isinstance(donnees.get("corrections"), list):
        raise PannePhase(phase, 'racine non conforme au schéma (attendu : {"corrections": [...]})')

    validees: list[Correction] = []
    for index, entree in enumerate(donnees["corrections"]):
        try:
            correction = Correction.model_validate(entree)
        except ValidationError as erreur:
            JOURNAL.warning("Correction %d rejetée (%s) : %s", index, phase, str(erreur)[:300])
            continue
        if correction.phase != phase:
            # La phase est connue par construction : cohérence forcée (v6 §8.2)
            correction = correction.model_copy(update={"phase": phase})
        if correction.phase == "forme" and correction.original == correction.correction:
            # No-op Forme (jalon A, décision 34) : « cous » barré pour réécrire
            # « cous » (explication « aucune correction nécessaire ») n'est pas
            # une correction — rejet individuel, sans arrêter le pipeline.
            # NB : Style/Technique marquent SANS réécrire (original ==
            # correction est leur mode de marquage légitime — on ne les touche pas).
            JOURNAL.warning(
                "Correction %s rejetée (%s) : no-op Forme (original == correction)",
                correction.id, phase,
            )
            continue
        validees.append(correction)
    return validees


def reconcilier(correction: Correction, paragraphe: Paragraphe) -> Correction | None:
    """Vérifie l'invariant `paragraphe[debut:fin] == original`, sinon répare par
    recherche ancrée, sinon occurrence unique, sinon rejet (v6 §8.3)."""
    texte = paragraphe.texte
    if texte[correction.debut:correction.fin] == correction.original:
        return correction

    # 1. Recherche ancrée : contexte_avant + original contigus (v6 §8.3)
    if correction.contexte_avant:
        ancre = correction.contexte_avant + correction.original
        position = texte.find(ancre)
        if position != -1:
            fin = position + len(ancre)
            return correction.model_copy(update={"debut": fin - len(correction.original), "fin": fin})

    # 2. Occurrence unique : retrouvée de façon certaine (v6 §8.3)
    occurrences = [m.start() for m in re.finditer(re.escape(correction.original), texte)]
    if len(occurrences) == 1:
        debut = occurrences[0]
        return correction.model_copy(update={"debut": debut, "fin": debut + len(correction.original)})

    # 3. Ambigu ou introuvable : correction écartée, consignée en debug (v6 §8.3)
    JOURNAL.warning(
        "Correction %s écartée : fragment %r introuvable ou ambigu dans %s",
        correction.id, correction.original, paragraphe.id,
    )
    return None


def renumeroter(corrections: list[Correction]) -> list[Correction]:
    """Assigne des ids GLOBAUX uniques et déterministes (jalon A, décision 33).

    Chaque phase LLM émet ses propres ids (ex. `c-0001`) sans coordination :
    deux corrections de phases différentes peuvent partager le même id. Or
    `rendu.py` construit ses groupes `g-XXXX` par id — un doublon colle deux
    corrections (barre latérale désynchronisée, choix Forme partagé).
    On réassigne donc `c-0001`, `c-0002`, … dans l'ordre de la liste, qui est
    déterministe (phases dans ORDRE_PHASES, ordre d'émission du LLM)."""
    return [
        c.model_copy(update={"id": f"c-{index:04d}"})
        for index, c in enumerate(corrections, start=1)
    ]


# (R1-b) L'ancienne `dedupliquer()` (v6 §8.4 : Style prioritaire, Embellissement
# migré dans le tooltip du Style) est SUPPRIMÉE — décision consignée au commit :
# elle ne faisait plus rien d'utile et la « déduplication » est désormais une
# règle d'AFFICHAGE (rendu.py : couches superposées dans « Tout », séparées par
# onglet). Aucune correction n'est absorbée en réconciliation.
