"""Préparation du document annoté — v6 §7 et §13.

Fonctions PURES : fusion des chevauchements en blocs contigus, identifiants
`g-XXXX` calculés par Python (jamais fournis par les LLM — v6 §0-8), compteur
des paragraphes masqués. Seuls les paragraphes comportant au moins une correction
sont affichés (v6 §7.1). L'échappement HTML est assuré par Jinja2 (autoévasion).

Rendu (v6 §7.3) :
- correction simple : <del> barré + <ins> coloré + tooltip ;
- bloc multi : <del class="del--multi"> (union des intervalles, jamais barré)
  + <ins> ordonnés Forme -> Style -> Technique -> Embellissement + tooltip multi-cas ;
- embellissement isolé : <mark class="sugg"> jamais barré + tooltip ;
- embellissement migré : section « Embellissement — suggestions » du tooltip Style (v6 §8.4)."""

from app.models import CorrectionFusionnee
from app.services.normalisation import Paragraphe

ORDRE_PHASES = ["forme", "style", "technique", "embellissement"]
LIBELLES = {
    "forme": "Forme",
    "style": "Style",
    "technique": "Technique",
    "embellissement": "Embellissement",
}


def _cas(fusion: CorrectionFusionnee) -> dict:
    """Un cas de tooltip : titre, explication, règle, variantes (+ embellissement migré)."""
    correction = fusion.correction
    cas = {
        "phase": correction.phase,
        "titre": f"{LIBELLES[correction.phase]} — {correction.type.replace('_', ' ')}",
        "explication": correction.explication,
        "regle": correction.regle,
        "variantes": list(correction.variantes),
        "non_contraignante": correction.phase == "embellissement",
    }
    if fusion.embellissement_migre is not None:
        migre = fusion.embellissement_migre
        cas["embellissement"] = {
            "suggestion": migre.suggestion,
            "variantes": list(migre.variantes),
            "explication": migre.explication,
        }
    return cas


def preparer_document(
    fusionnees: list[CorrectionFusionnee], paragraphes: list[Paragraphe]
) -> dict:
    """Retourne {'paragraphes': [...segments...], 'nb_masques': int} pour le template E5."""
    par_corrections: dict[str, list[CorrectionFusionnee]] = {}
    for fusion in fusionnees:
        par_corrections.setdefault(fusion.correction.paragraphe_id, []).append(fusion)

    affiches: list[dict] = []
    nb_masques = 0
    numero_groupe = 0
    for paragraphe in paragraphes:
        items = par_corrections.get(paragraphe.id)
        if not items:
            nb_masques += 1
            continue
        tries = sorted(items, key=lambda f: (f.correction.debut, f.correction.fin))
        numero_groupe, segments = _construire_segments(tries, paragraphe, numero_groupe)
        affiches.append({"id": paragraphe.id, "segments": segments})
    return {"paragraphes": affiches, "nb_masques": nb_masques}


def _construire_segments(items, paragraphe, numero_groupe):
    """Regroupe les corrections qui se chevauchent (union contiguë) puis découpe
    le paragraphe en segments texte/correction."""
    blocs: list[dict] = []
    for fusion in items:
        correction = fusion.correction
        if blocs and correction.debut < blocs[-1]["fin"]:  # intersection
            blocs[-1]["items"].append(fusion)
            blocs[-1]["fin"] = max(blocs[-1]["fin"], correction.fin)
        else:
            blocs.append({"items": [fusion], "debut": correction.debut, "fin": correction.fin})

    segments: list[dict] = []
    position = 0
    for bloc in blocs:
        if bloc["debut"] > position:
            segments.append({"type": "texte", "texte": paragraphe.texte[position:bloc["debut"]]})
        numero_groupe += 1
        segments.append(_segment_du_bloc(bloc, paragraphe, f"g-{numero_groupe:04d}"))
        position = bloc["fin"]
    if position < len(paragraphe.texte):
        segments.append({"type": "texte", "texte": paragraphe.texte[position:]})
    return numero_groupe, segments


def _segment_du_bloc(bloc, paragraphe, groupe: str) -> dict:
    """Bloc d'une ou plusieurs corrections chevauchantes (v6 §7.3)."""
    original = paragraphe.texte[bloc["debut"]:bloc["fin"]]
    items = bloc["items"]

    if len(items) == 1:
        fusion = items[0]
        correction = fusion.correction
        if correction.phase == "embellissement":
            # Suggestion isolée, jamais barrée (v6 §7.3.3)
            return {
                "type": "suggestion",
                "groupe": groupe,
                "original": original,
                "suggestion": correction.correction,
                "explication": correction.explication,
                "regle": correction.regle,
                "variantes": list(correction.variantes),
            }
        return {
            "type": "simple",
            "groupe": groupe,
            "phase": correction.phase,
            "original": original,
            "texte": correction.correction,
            "cas": [_cas(fusion)],
        }

    tries = sorted(items, key=lambda f: ORDRE_PHASES.index(f.correction.phase))
    return {
        "type": "multi",
        "groupe": groupe,
        "original": original,
        "ins": [
            {"phase": f.correction.phase, "texte": f.correction.correction} for f in tries
        ],
        "cas": [_cas(f) for f in tries],
    }
