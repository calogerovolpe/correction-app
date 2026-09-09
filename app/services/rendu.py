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

Entrées (jalon R2) : soit les paramètres historiques `(paragraphes, entrees,
choix, modifies)` VUES DU TEXTE COURANT projeté (via
`reconstruction.projeter_paragraphes`), soit — point d'entrée recommandé —
`preparer_document_depuis_etat(etat, onglet)` qui projette depuis la base
immuable + annotations puis délègue ici. Le compteur de paragraphes masqués ne
compte que les paragraphes sans correction active ET sans modification manuelle.
"""

from app.services import reconstruction
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
    c = entree["correction"]
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
    groupes = {e["correction"].id: f"g-{i + 1:04d}" for i, e in enumerate(entrees)}
    infos_barre = [_info(e, groupes[e["correction"].id]) for e in entrees]
    for info in infos_barre:
        if info["phase"] == "forme":
            info["decision"] = "original" if choix.get(info["id"]) == "original" else "corrige"

    affiches: list[dict] = []
    nb_masques = 0
    modifies_set = set(modifies or [])
    for p in paragraphes:
        entrees_pid = [
            e for e in entrees if e["correction"].paragraphe_id == p.id
        ]
        actives = [e for e in entrees_pid if e["etat"] == "active"]
        if not actives and p.id not in modifies_set:
            nb_masques += 1
        # FA3 — document COMPLET : TOUS les paragraphes sont exposés (les
        # paragraphes propres ne sont plus retirés de la réponse) ; le toggle
        # client « masquer » filtre en mémoire sur cette liste complète.
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


def preparer_document_depuis_etat(etat: dict, phase: str = "tout") -> dict:
    """Point d'entrée du rendu (jalon R2) : projette le texte COURANT depuis la
    BASE IMMUABLE + annotations (`reconstruction.projeter_paragraphes`), puis
    délègue à `preparer_document` — AUCUNE logique de segments dupliquée. La
    liste des corrections projetées sert telle quelle à la barre latérale.
    `phase` = onglet (« tout » = superposition complète). Zéro appel LLM."""
    paragraphes, entrees = reconstruction.projeter_paragraphes(etat)
    if phase != "tout":
        entrees = [e for e in entrees if e["correction"].phase == phase]
    return preparer_document(
        paragraphes, entrees,
        etat.get("choix", {}), etat.get("modifies", []),
    )


def _classe_marque(entree: dict) -> str:
    phase = entree["correction"].phase
    if phase in _CLASSE_MARQUE:
        return _CLASSE_MARQUE[phase]
    return "refusee"  # correction Forme refusée : texte original restauré


def _couvrants(marques: list[dict], a: int, b: int) -> list[dict]:
    return [
        e for e in marques
        if e["correction"].debut < b and e["correction"].fin > a
    ]


def _segments(p: ParagrapheRiche, actives: list[dict], choix: dict, groupes: dict) -> list[dict]:
    """Segments du paragraphe — FA3 : segmentation ATOMIQUE aux bornes.

    Les points de découpe fusionnent les bornes du paragraphe, de chaque Forme
    appliquée et de chaque marque (Style/Technique/Forme refusée) : une
    annotation ne déborde JAMAIS sur le texte voisin d'un même run Word (fin du
    sur-marquage au run entier). Les classes se CUMULENT sur un segment couvert
    par plusieurs marques ; un bloc Forme n'est émis qu'une seule fois (les
    intervalles internes à sa zone sont absorbés par le bloc del/ins entier)."""
    texte = extraire_texte_brut_paragraphe(p)
    formes_actives = sorted(
        (
            e for e in actives
            if e["correction"].phase == "forme"
            and choix.get(e["correction"].id) != "original"
        ),
        key=lambda e: e["correction"].debut,
    )
    marques = [
        e for e in actives
        if e["correction"].phase != "forme"
        or choix.get(e["correction"].id) == "original"
    ]
    points = {0, len(texte)}
    for entree in formes_actives + marques:
        points.add(max(0, entree["correction"].debut))
        points.add(min(len(texte), entree["correction"].fin))
    bornes = sorted(points)
    segments: list[dict] = []
    forme_emise: str | None = None
    for a, b in zip(bornes, bornes[1:]):
        if a >= b:
            continue
        forme = next(
            (
                e for e in formes_actives
                if e["correction"].debut <= a and b <= e["correction"].fin
            ),
            None,
        )
        if forme is not None:
            if forme_emise != forme["correction"].id:
                segments.append(
                    _segment_forme(forme, p, forme["correction"], marques, groupes)
                )
                forme_emise = forme["correction"].id
            continue
        segments.extend(_segments_texte(p, a, b, marques, groupes))
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
        groupe = groupes[couvrants[0]["correction"].id] if couvrants else None
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

