"""Préparation du document annoté et des données pour la barre latérale et les bulles contextuelles (J2.2).

Modèle interactif J2.2 :
1. Forme (rouge) : barré conservé (`<del>` original + `<ins>` correction). Affichage détails dans la barre latérale.
2. Technique (violet) : pas d'altération dans le corps, uniquement listé dans la barre latérale (section Technique).
3. Style (bleu) : soulignement bleu pointillé sur le fragment original (non barré). Clic -> bulle contextuelle + bouton "Demander des alternatives".
4. Embellissement (vert) : surlignage/soulignage discret vert pointillé. Clic -> bulle contextuelle + bouton "Demander des suggestions".
"""

from app.models import CorrectionFusionnee
from app.services.normalisation import Paragraphe

ORDRE_PHASES = ["forme", "style", "technique", "embellissement"]
LIBELLES = {
    "forme": "Forme",
    "style": "Style",
    "technique": "Technique",
    "embellissement": "Embellissement",
}


def _info_correction(fusion: CorrectionFusionnee, groupe: str) -> dict:
    c = fusion.correction
    return {
        "id": c.id,
        "groupe": groupe,
        "phase": c.phase,
        "type": c.type,
        "paragraphe_id": c.paragraphe_id,
        "debut": c.debut,
        "fin": c.fin,
        "original": c.original,
        "correction": c.correction,
        "explication": c.explication,
        "regle": c.regle,
        "titre": f"{LIBELLES.get(c.phase, c.phase.capitalize())} — {c.type.replace('_', ' ')}",
    }


def preparer_document(
    fusionnees: list[CorrectionFusionnee],
    paragraphes: list[Paragraphe],
    paragraphes_riches: list = None,
) -> dict:
    """Construit le document annoté avec les segments pour le texte,
    et la liste structurée des corrections pour la barre latérale.
    Si paragraphes_riches est fourni, préserve le formatage (gras, italique, souligné)
    sur les segments de texte non corrigés.
    """
    
    # Isoler les corrections techniques (qui vont exclusivement dans la barre latérale)
    corrections_techniques = [
        _info_correction(f, f"tech-{i+1:04d}")
        for i, f in enumerate(f for f in fusionnees if f.correction.phase == "technique")
    ]

    # Corrections in-text : Forme, Style, Embellissement
    in_text_fusions = [f for f in fusionnees if f.correction.phase != "technique"]

    par_corrections: dict[str, list[CorrectionFusionnee]] = {}
    for fusion in in_text_fusions:
        par_corrections.setdefault(fusion.correction.paragraphe_id, []).append(fusion)

    # Indexation des paragraphes riches par identifiant
    riches_par_id = {p.id: p for p in (paragraphes_riches or [])}

    affiches: list[dict] = []
    toutes_corrections_barre: list[dict] = []
    nb_masques = 0
    numero_groupe = 0

    for paragraphe in paragraphes:
        items = par_corrections.get(paragraphe.id)
        if not items:
            nb_masques += 1
            continue

        p_riche = riches_par_id.get(paragraphe.id)
        tries = sorted(items, key=lambda f: (f.correction.debut, f.correction.fin))
        numero_groupe, segments, corrections_groupe = _construire_segments(
            tries, paragraphe, numero_groupe, p_riche
        )
        affiches.append({"id": paragraphe.id, "segments": segments})
        toutes_corrections_barre.extend(corrections_groupe)

    return {
        "paragraphes": affiches,
        "nb_masques": nb_masques,
        "corrections_barre": toutes_corrections_barre,
        "corrections_techniques": corrections_techniques,
    }


def _generer_segments_texte(debut: int, fin: int, paragraphe: Paragraphe, p_riche) -> list[dict]:
    """Génère un ou plusieurs segments de texte brut ou enrichis en runs si p_riche est présent."""
    if debut >= fin:
        return []
    if not p_riche:
        return [{"type": "texte", "texte": paragraphe.texte[debut:fin]}]

    from app.services.texte_riche import decouper_runs_par_intervalle
    _, runs_intervalle, _ = decouper_runs_par_intervalle(p_riche.runs, debut, fin)
    segments = []
    for r in runs_intervalle:
        segments.append({
            "type": "texte",
            "texte": r.texte,
            "gras": r.gras,
            "italique": r.italique,
            "souligne": r.souligne,
        })
    return segments


def _construire_segments(items, paragraphe, numero_groupe, p_riche=None):
    blocs: list[dict] = []
    for fusion in items:
        correction = fusion.correction
        if blocs and correction.debut < blocs[-1]["fin"]:
            blocs[-1]["items"].append(fusion)
            blocs[-1]["fin"] = max(blocs[-1]["fin"], correction.fin)
        else:
            blocs.append({"items": [fusion], "debut": correction.debut, "fin": correction.fin})

    segments: list[dict] = []
    corrections_creees: list[dict] = []
    position = 0

    for bloc in blocs:
        if bloc["debut"] > position:
            segments.extend(_generer_segments_texte(position, bloc["debut"], paragraphe, p_riche))

        numero_groupe += 1
        groupe_id = f"g-{numero_groupe:04d}"
        segment, infos = _segment_du_bloc(bloc, paragraphe, groupe_id)
        segments.append(segment)
        corrections_creees.extend(infos)
        position = bloc["fin"]

    if position < len(paragraphe.texte):
        segments.extend(_generer_segments_texte(position, len(paragraphe.texte), paragraphe, p_riche))

    return numero_groupe, segments, corrections_creees


def _segment_du_bloc(bloc, paragraphe, groupe: str) -> tuple[dict, list[dict]]:
    original = paragraphe.texte[bloc["debut"]:bloc["fin"]]
    items = bloc["items"]

    infos_corrections = [_info_correction(f, groupe) for f in items]

    if len(items) == 1:
        fusion = items[0]
        c = fusion.correction
        info = infos_corrections[0]

        if c.phase == "style":
            # Répétitions / Style : soulignement pointillé bleu, original non altéré par défaut
            return {
                "type": "style",
                "groupe": groupe,
                "original": original,
                "paragraphe_id": c.paragraphe_id,
                "info": info,
            }, infos_corrections

        elif c.phase == "embellissement":
            # Embellissement : discret pointillé vert, original non altéré par défaut
            return {
                "type": "embellissement",
                "groupe": groupe,
                "original": original,
                "paragraphe_id": c.paragraphe_id,
                "info": info,
            }, infos_corrections

        else:
            # Forme : barré + ins rouge
            return {
                "type": "forme",
                "groupe": groupe,
                "original": original,
                "correction": c.correction,
                "paragraphe_id": c.paragraphe_id,
                "info": info,
            }, infos_corrections

    # Bloc multi (ex: Forme + Style)
    return {
        "type": "multi",
        "groupe": groupe,
        "original": original,
        "paragraphe_id": items[0].correction.paragraphe_id,
        "infos": infos_corrections,
    }, infos_corrections

