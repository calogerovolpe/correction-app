"""Préparation du document annoté — couches superposables (jalon J2.5).

Chaque phase garde SA couche visuelle, même en cas de chevauchement (décision
de l'auteur, J2.5) :
- Forme : original barré + correction insérée en rouge ;
- Style : soulignement pointillé bleu (mark-style) ;
- Technique : fond jaune (mark-technique), ET section dédiée de la barre latérale ;
- une correction Forme refusée (« Garder l'original ») : texte neutre marqué
  `refusee` (repérable, non appliqué).
Les corrections de phases différentes couvrant un même mot s'empilent par
classes CSS cumulées — jamais avalées par un bloc fusionné.

Entrées : l'état courant de `reconstruction` (texte courant + corrections en
coordonnées courantes + choix). Le compteur de paragraphes masqués ne compte
que les paragraphes sans correction active ET sans modification manuelle.
"""

from app.services.texte_riche import (
    ParagrapheRiche,
    RunFormat,
    extraire_texte_brut_paragraphe,
)

LIBELLES = {
    "forme": "Forme",
    "style": "Style",
    "technique": "Technique",
    "embellissement": "Embellissement",
}

_CLASSE_MARQUE = {"style": "mark-style", "technique": "mark-technique"}


def _info(entree: dict, groupe: str) -> dict:
    c = entree["fusion"].correction
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
        "etat": entree["etat"],
        "motif": entree["motif"],
    }


def preparer_document(
    paragraphes: list[ParagrapheRiche],
    entrees: list[dict],
    choix: dict,
    modifies: list[str] | None = None,
) -> dict:
    """Construit le document annoté (couches) + la liste pour la barre latérale."""
    groupes = {e["fusion"].correction.id: f"g-{i + 1:04d}" for i, e in enumerate(entrees)}
    infos_barre = [_info(e, groupes[e["fusion"].correction.id]) for e in entrees]
    for info in infos_barre:
        if info["phase"] == "forme":
            info["decision"] = "original" if choix.get(info["id"]) == "original" else "corrige"

    affiches: list[dict] = []
    nb_masques = 0
    modifies_set = set(modifies or [])
    for p in paragraphes:
        entrees_pid = [
            e for e in entrees if e["fusion"].correction.paragraphe_id == p.id
        ]
        actives = [e for e in entrees_pid if e["etat"] == "active"]
        if not actives and p.id not in modifies_set:
            nb_masques += 1
            continue
        affiches.append({
            "id": p.id,
            "segments": _segments(p, actives, choix, groupes),
            "edite": p.id in modifies_set,
        })
    return {
        "paragraphes": affiches,
        "nb_masques": nb_masques,
        "corrections_barre": infos_barre,
    }


def preparer_document_par_phase(
    paragraphes: list[ParagrapheRiche],
    entrees: list[dict],
    phase: str,
    choix: dict,
    modifies: list[str] | None = None,
) -> dict:
    """Projection d'UN onglet (jalon R1-a) : ne conserve que les corrections de
    `phase`, puis délègue à `preparer_document` — AUCUNE logique de segments
    dupliquée. `preparer_document()` reste la projection « Tout » (superposition)."""
    filtrees = [e for e in entrees if e["fusion"].correction.phase == phase]
    return preparer_document(paragraphes, filtrees, choix, modifies)


def _classe_marque(entree: dict) -> str:
    phase = entree["fusion"].correction.phase
    if phase in _CLASSE_MARQUE:
        return _CLASSE_MARQUE[phase]
    return "refusee"  # correction Forme refusée : texte original restauré


def _couvrants(marques: list[dict], a: int, b: int) -> list[dict]:
    return [
        e for e in marques
        if e["fusion"].correction.debut < b and e["fusion"].correction.fin > a
    ]


def _segments(p: ParagrapheRiche, actives: list[dict], choix: dict, groupes: dict) -> list[dict]:
    texte = extraire_texte_brut_paragraphe(p)
    formes = sorted(
        (
            e for e in actives
            if e["fusion"].correction.phase == "forme"
            and choix.get(e["fusion"].correction.id) != "original"
        ),
        key=lambda e: e["fusion"].correction.debut,
    )
    marques = [
        e for e in actives
        if e["fusion"].correction.phase != "forme"
        or choix.get(e["fusion"].correction.id) == "original"
    ]
    segments: list[dict] = []
    position = 0
    for entree in formes:
        c = entree["fusion"].correction
        if c.debut > position:
            segments.extend(_segments_texte(p, position, c.debut, marques, groupes))
        segments.append(_segment_forme(entree, p, c, marques, groupes))
        position = c.fin
    if position < len(texte):
        segments.extend(_segments_texte(p, position, len(texte), marques, groupes))
    return segments


def _runs_intervalle(runs: list[RunFormat], a: int, b: int) -> list[RunFormat]:
    """Runs (tronqués aux bornes) couvrant [a, b)."""
    morceaux: list[RunFormat] = []
    position = 0
    for run in runs:
        d, f = position, position + len(run.texte)
        position = f
        if f <= a or d >= b:
            continue
        morceaux.append(RunFormat(
            texte=run.texte[max(d, a) - d:min(f, b) - d],
            gras=run.gras, italique=run.italique, souligne=run.souligne,
        ))
    return morceaux


def _segments_texte(
    p: ParagrapheRiche, a: int, b: int, marques: list[dict], groupes: dict
) -> list[dict]:
    items: list[dict] = []
    position = a
    for run in _runs_intervalle(p.runs, a, b):
        couvrants = _couvrants(marques, position, position + len(run.texte))
        position += len(run.texte)
        classes = " ".join(sorted({_classe_marque(e) for e in couvrants}))
        groupe = groupes[couvrants[0]["fusion"].correction.id] if couvrants else None
        items.append({
            "type": "texte",
            "texte": run.texte,
            "gras": run.gras,
            "italique": run.italique,
            "souligne": run.souligne,
            "classes": classes,
            "groupe": groupe,
        })
    return items


def _segment_forme(
    entree: dict, p: ParagrapheRiche, c, marques: list[dict], groupes: dict
) -> dict:
    couvrants = _couvrants(marques, c.debut, c.fin)
    classes = " ".join(sorted({_classe_marque(e) for e in couvrants}))
    runs_zone = _runs_intervalle(p.runs, c.debut, c.fin)
    premier = runs_zone[0] if runs_zone else RunFormat(texte="")
    return {
        "type": "forme",
        "groupe": groupes[c.id],
        "del": c.original,
        "ins": "".join(run.texte for run in runs_zone),
        "gras": premier.gras,
        "italique": premier.italique,
        "souligne": premier.souligne,
        "classes": classes,
    }

