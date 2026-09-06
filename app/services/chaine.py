"""Machine à états de la chaîne N+1 et remplacement officiel — v6 §6.5 et §6.6.

Fonctions PURES (sans LLM ni écriture) : les écritures et le reclassement
sont appliqués par l'orchestration (J2) selon la décision retournée.

Règles (v6 §6.5) :
1. N+1 conforme -> chapitre officiel ;
2. N=N AVEC remplacement explicite (/maj) -> remplacement officiel ;
3. N=N SANS remplacement -> rupture -> reclassement en Extrait ;
4. Tout le reste (trou, antérieur, décimal, Prologue hors séquence) -> rupture -> Extrait ;
5. /passage ou /extrait -> aucune vérification de chaîne.
Le numéro courant n'est JAMAIS modifié par un reclassement (v6 §6.5)."""

from dataclasses import dataclass
from typing import Literal

Decision = Literal[
    "conforme",              # chapitre N+1 officiel
    "remplacement_officiel",  # N=N avec remplacement demandé (v6 §6.6)
    "reclassement_extrait",   # rupture -> Extrait, correction livrée (v6 §6.5 règle 4)
    "refus_remplacement",     # préconditions /maj non remplies (v6 §6.6)
    "hors_chaine",            # texte non chapitre : Passage/Extrait natif
    "forcage",                # /passage ou /extrait (v6 §6.5 règle 5)
]

MESSAGE_RECLASSEMENT = (
    "Chapitre hors séquence — traité comme Extrait (suggestions d'embellissement "
    "incluses) ; le codex n'a pas été modifié. Resoumettez avec le bon numéro pour "
    "entrer dans la chaîne officielle."
)


@dataclass(frozen=True)
class Arbitrage:
    """Résultat de l'arbitrage de chaîne — catégorie définitive et message éventuel."""
    decision: Decision
    categorie: str  # 'chapitre' | 'passage' | 'extrait' (vide si gérée en aval)
    numero: float | None
    message: str | None = None


def numero_attendu(projet: dict) -> float | None:
    """Numéro attendu (v6 §6.5) : session vierge -> Prologue (0) ou 1 (None) ;
    sinon courant + 1. Jamais modifié par un reclassement."""
    courant = projet.get("current_chapter_num")
    if courant is None:
        return None
    return float(courant) + 1


def arbitrer(
    projet: dict,
    numero_recu: float | None,
    categorie_forcee: str | None = None,
    remplacement_demande: bool = False,
    categorie_naturelle: str = "extrait",
) -> Arbitrage:
    """Arbitrage complet de la chaîne (v6 §6.5) — pur, sans LLM ni écriture."""

    # Règle 5 : forçage /passage ou /extrait -> aucune vérification de chaîne
    if categorie_forcee in ("passage", "extrait"):
        return Arbitrage(decision="forcage", categorie=categorie_forcee, numero=None)

    # Pas un chapitre (aucun titre) -> hors chaîne, catégorie naturelle du texte
    if numero_recu is None:
        return Arbitrage(decision="hors_chaine", categorie=categorie_naturelle, numero=None)

    # Numéro décimal -> rupture (v6 §6.5 règle 4)
    if numero_recu != int(numero_recu):
        return Arbitrage("reclassement_extrait", "extrait", numero_recu, MESSAGE_RECLASSEMENT)

    courant = projet.get("current_chapter_num")

    # Session vierge : attendu = Prologue (0) ou Chapitre 1 (v6 §6.5)
    if courant is None:
        if numero_recu in (0.0, 1.0):
            return Arbitrage("conforme", "chapitre", numero_recu)
        return Arbitrage("reclassement_extrait", "extrait", numero_recu, MESSAGE_RECLASSEMENT)

    # Règle 1 : chapitre conforme N+1
    if numero_recu == float(courant) + 1:
        return Arbitrage("conforme", "chapitre", numero_recu)

    # Règles 2-3 : N=N -> remplacement officiel UNIQUEMENT si demandé
    if numero_recu == float(courant):
        if remplacement_demande:
            return Arbitrage("remplacement_officiel", "chapitre", numero_recu)
        return Arbitrage(
            "reclassement_extrait", "extrait", numero_recu,
            "Chapitre déjà officiel — resoumission sans remplacement : traitée comme "
            "Extrait, codex non modifié. Cochez « Remplacer le chapitre courant » pour "
            "officialiser un remplacement.",
        )

    # Règle 4 : tout le reste = rupture -> reclassement en Extrait
    return Arbitrage("reclassement_extrait", "extrait", numero_recu, MESSAGE_RECLASSEMENT)


def valider_remplacement(
    projet: dict,
    chapitres_existants: set[int],
    numero: int | None,
) -> Arbitrage:
    """Préconditions du remplacement officiel (v6 §6.6), vérifiées par Python
    AVANT toute analyse — refus zéro token si invalide :
      1. N doit exister dans `chapitres` (jamais de /maj pour un chapitre jamais soumis) ;
      2. N doit être égal au chapitre courant (N=N)."""
    courant = projet.get("current_chapter_num")
    cible = numero if numero is not None else courant

    if cible is None:
        return Arbitrage(
            "refus_remplacement", "extrait", None,
            "Aucun chapitre officiel : impossible de remplacer un chapitre jamais soumis.",
        )
    if int(cible) not in chapitres_existants:
        return Arbitrage(
            "refus_remplacement", "extrait", cible,
            f"Le chapitre {int(cible)} n'a jamais été soumis : remplacement impossible.",
        )
    if courant is None or int(cible) != int(courant):
        return Arbitrage(
            "refus_remplacement", "extrait", cible,
            f"Le remplacement ne s'applique qu'au chapitre courant (attendu N=N, "
            f"reçu {int(cible)}).",
        )
    return Arbitrage("remplacement_officiel", "chapitre", float(cible))
