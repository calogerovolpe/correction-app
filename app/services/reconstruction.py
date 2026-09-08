"""Reconstruction de l'état courant du texte — atelier E5 (spec §8, jalons J2.5→R2).

Règle de mission : la version validée ou soumise est EXACTEMENT le texte
affiché à l'écran au moment du clic. Depuis le jalon R2, l'état est un modèle
« base immuable + annotations » (persistance : table `documents`) :

- `base` : le texte normalisé D'ORIGINE (runs riches), JAMAIS muté — les
  corrections et modifications manuelles y sont exprimées en coordonnées de la
  BASE (jamais décalées) ;
- `corrections` : les corrections, toutes en coordonnées de la base. Chaque
  entrée porte `etat` ('active' | 'obsolete') et `motif` ;
- `choix` : refus explicites de corrections Forme ({id: "original"}) ;
- `patches` : les modifications MANUELLES (alternative / embellissement),
  remplacements `{paragraphe_id, debut, fin, texte}` en coordonnées de la base ;
- `modifies` : identifiants des paragraphes modifiés à la main (le bouton
  « Réévaluer » leur est proposé).

« Texte courant » = PROJECTION calculée : base + patches manuels + corrections
Forme acceptées (triés, appliqués une seule fois), chaque fragment étant soit
du texte de base, soit un remplacement. Refuser une Forme = la retirer du
filtre (aucun remappage). Style/Technique = marquage sur la base, jamais de
réécriture. Les corrections ne sont plus jamais « décalées » : elles portent
leurs offsets d'origine (base), et le rendu les projette sur le texte courant.

Les corrections Forme qui se chevauchent entre elles : la première garde la
main, les suivantes sont obsolètes (« chevauche une autre correction »).
Ajouter une modification manuelle rend obsolètes les Forme actives
intersectées ; une modification qui recouvrirait un patch manuel existant est
REFUSÉE (`ZoneDejaModifiee`) — réévaluez le paragraphe ou choisissez un autre
passage.
"""

import json
import logging
import re

from app.models import Correction
from app.services.texte_riche import (
    ParagrapheRiche,
    RunFormat,
    decouper_runs_par_intervalle,
    extraire_texte_brut_paragraphe,
)

JOURNAL = logging.getLogger("correction.reconstruction")

MODELE_ETAT = 2


class ZoneDejaModifiee(Exception):
    """La sélection demandée ne peut pas être ancrée proprement sur la base
    immuable (elle recouvre partiellement une zone déjà modifiée à la main)."""


# --- Fabrique de l'état ------------------------------------------------------


def etat_initial(
    corrections: list[Correction], paragraphes: list[ParagrapheRiche]
) -> dict:
    """État courant initial (jalon R2) : la base immuable D'ORIGINE est
    conservée telle quelle — aucune Forme n'est spliée dans le texte ; elle
    sont appliquées par la PROJECTION. Les Forme qui se chevauchent sont
    d'abord marquées obsolètes (règle héritée de J2.5, en coordonnées base)."""
    etat: dict = {
        "modele": MODELE_ETAT,
        "base": [p.model_copy(deep=True) for p in paragraphes],
        "corrections": [
            {"correction": c, "etat": "active", "motif": None} for c in corrections
        ],
        "choix": {},
        "patches": [],
        "modifies": [],
    }
    for pid in {p.id for p in etat["base"]}:
        _resoudre_chevauchements_formes(etat, pid)
    return etat


def _resoudre_chevauchements_formes(etat: dict, paragraphe_id: str) -> None:
    """Les corrections Forme actives qui se chevauchent : la première garde la
    main, les suivantes sont obsolètes (coordonnées BASE — jamais décalées)."""
    formes = [
        e for e in etat["corrections"]
        if e["correction"].paragraphe_id == paragraphe_id
        and e["correction"].phase == "forme" and e["etat"] == "active"
    ]
    resolues: list[dict] = []
    for entree in sorted(
        formes, key=lambda e: (e["correction"].debut, e["correction"].fin)
    ):
        c = entree["correction"]
        if any(
            c.debut < f and c.fin > d
            for d, f in ((r["correction"].debut, r["correction"].fin) for r in resolues)
        ):
            entree["etat"] = "obsolete"
            entree["motif"] = "Chevauche une autre correction Forme — non appliquée."
        else:
            resolues.append(entree)


# --- Projection du texte courant --------------------------------------------


def _fragments(etat: dict, paragraphe_id: str) -> list[dict]:
    """Fragments de projection d'un paragraphe : le texte courant s'obtient en
    concaténant les fragments (dans l'ordre). Chaque fragment est soit du TEXTE
    DE BASE (`texte` None, porté [debut, fin) en coordonnées base), soit un
    REMPLACEMENT (`texte` donné). Les fragments se recouvrent sans gap et le
    recouvrement éventuel est résolu de façon déterministe : les Forme passent
    APRÈS les patches manuels (donc gagnent en cas de chevauchement — cas des
    corrections de réévaluation ancrées sur une zone manuelle)."""
    paragraphe = _paragraphe(etat, paragraphe_id)
    longueur = len(extraire_texte_brut_paragraphe(paragraphe))
    remplacements: list[tuple[int, int, str]] = []
    for patch in etat.get("patches", []):
        if patch["paragraphe_id"] == paragraphe_id:
            remplacements.append((patch["debut"], patch["fin"], patch["texte"]))
    for entree in etat["corrections"]:
        c = entree["correction"]
        if (
            c.paragraphe_id == paragraphe_id
            and entree["etat"] == "active"
            and c.phase == "forme"
            and etat.get("choix", {}).get(c.id) != "original"
        ):
            remplacements.append((c.debut, c.fin, c.correction))
    remplacements.sort(key=lambda r: (r[0], r[1]))

    fragments: list[dict] = [{"debut": 0, "fin": longueur, "texte": None}]
    for debut, fin, texte in remplacements:
        if fin <= debut:
            continue
        nouveaux: list[dict] = []
        for frag in fragments:
            if frag["fin"] <= debut or frag["debut"] >= fin:
                nouveaux.append(frag)
                continue
            if frag["debut"] < debut:
                nouveaux.append(dict(frag, fin=debut))
            nouveaux.append({
                "debut": max(frag["debut"], debut),
                "fin": min(frag["fin"], fin),
                "texte": texte,
            })
            if frag["fin"] > fin:
                nouveaux.append(dict(frag, debut=fin))
        fragments = nouveaux

    position = 0
    for frag in fragments:
        longueur_frag = (
            len(frag["texte"])
            if frag["texte"] is not None
            else frag["fin"] - frag["debut"]
        )
        frag["proj_debut"] = position
        frag["proj_fin"] = position + longueur_frag
        position += longueur_frag
    return fragments


def _projeter_intervalle(fragments: list[dict], a: int, b: int) -> tuple[int, int]:
    """Position courante (texte projeté) d'un intervalle de la BASE [a, b) :
    s'il intersecte un remplacement → il couvre la plage projetée de ce
    remplacement ; sinon → décalé uniquement (sémantique de J2.5, sans jamais
    muter les offsets)."""
    for frag in fragments:
        if frag["texte"] is not None and a < frag["fin"] and b > frag["debut"]:
            return frag["proj_debut"], frag["proj_fin"]
    decal = 0
    for frag in fragments:
        if frag["texte"] is not None and frag["fin"] <= a:
            decal += len(frag["texte"]) - (frag["fin"] - frag["debut"])
    return a + decal, b + decal


def _convertir_vers_base(
    fragments: list[dict], debut_courant: int, fin_courant: int
) -> tuple[int, int]:
    """Retourne la zone de BASE couverte par un intervalle du texte COURANT
    [debut_courant, fin_courant). Idéale quand la sélection ne fait que
    traverser des fragments de base et/ou des remplacements ENTIERS ; toute
    sélection qui coupe un remplacement (zone déjà modifiée à la main) est
    refusée — impossible à ré-ancrer proprement sur la base."""
    if fin_courant <= debut_courant:
        return debut_courant, debut_courant
    base_debut: int | None = None
    base_fin: int | None = None
    for frag in fragments:
        pd, pf = frag["proj_debut"], frag["proj_fin"]
        if pf <= debut_courant or pd >= fin_courant:
            continue
        if frag["texte"] is None:
            d = frag["debut"] + max(0, debut_courant - pd)
            f = frag["fin"] - max(0, pf - fin_courant)
        else:
            if debut_courant < pd or pf < fin_courant:
                raise ZoneDejaModifiee(
                    "La sélection coupe une zone déjà modifiée par un "
                    "embellissement/une alternative — réévaluez le paragraphe "
                    "ou choisissez un autre passage."
                )
            d, f = frag["debut"], frag["fin"]
        if base_debut is None:
            base_debut, base_fin = d, f
        else:
            if d > base_fin:
                raise ZoneDejaModifiee(
                    "La sélection traverse une zone déjà modifiée — réévaluez "
                    "le paragraphe ou choisissez un autre passage."
                )
            base_fin = max(base_fin, f)
    if base_debut is None:
        raise ZoneDejaModifiee("La sélection ne correspond à aucun texte.")
    return base_debut, base_fin


def _runs_projetes(paragraphe: ParagrapheRiche, fragments: list[dict]) -> list[RunFormat]:
    """Reconstruit le texte courant EN RUNS (formatage Word préservé) : les
    fragments de base sont découpés depuis les runs de la base, les
    remplacements héritent du formatage du premier run couvert (règle J2.5)."""
    runs: list[RunFormat] = []
    for frag in fragments:
        if frag["texte"] is None:
            _, milieu, _ = decouper_runs_par_intervalle(
                paragraphe.runs, frag["debut"], frag["fin"]
            )
            runs.extend(milieu)
        else:
            _, morceaux, _ = decouper_runs_par_intervalle(
                paragraphe.runs, frag["debut"], frag["fin"]
            )
            premier = morceaux[0] if morceaux else None
            runs.append(RunFormat(
                texte=frag["texte"],
                gras=premier.gras if premier else False,
                italique=premier.italique if premier else False,
                souligne=premier.souligne if premier else False,
            ))
    return _fusionner_runs(runs)


def projeter_paragraphe(etat: dict, paragraphe_id: str) -> tuple[ParagrapheRiche, list[dict]]:
    """Projection d'UN paragraphe : (texte courant en runs, entrees de
    correction du paragraphe exprimées en coordonnées du texte courant)."""
    paragraphe = _paragraphe(etat, paragraphe_id)
    fragments = _fragments(etat, paragraphe_id)
    entrees: list[dict] = []
    for entree in etat["corrections"]:
        c = entree["correction"]
        if c.paragraphe_id != paragraphe_id:
            continue
        debut, fin = _projeter_intervalle(fragments, c.debut, c.fin)
        entrees.append({
            "correction": c.model_copy(update={"debut": debut, "fin": fin}),
            "etat": entree["etat"],
            "motif": entree["motif"],
        })
    return (
        ParagrapheRiche(id=paragraphe.id, runs=_runs_projetes(paragraphe, fragments)),
        entrees,
    )


def projeter_paragraphes(etat: dict) -> tuple[list[ParagrapheRiche], list[dict]]:
    """Projection de TOUS les paragraphes depuis la base immuable. Retourne
    (list[ParagrapheRiche], list[dict]) : les paragraphes du texte COURANT et
    toutes les entrées de correction exprimées en coordonnées du texte courant
    (la liste complète, servie à la barre latérale)."""
    projetes: list[ParagrapheRiche] = []
    entrees_projetees: list[dict] = []
    for paragraphe in etat["base"]:
        courant, entrees = projeter_paragraphe(etat, paragraphe.id)
        projetes.append(courant)
        entrees_projetees.extend(entrees)
    return projetes, entrees_projetees


def texte_paragraphe(etat: dict, paragraphe_id: str) -> str:
    """Texte COURANT (projeté) d'un paragraphe — what you see is what you get."""
    paragraphe = _paragraphe(etat, paragraphe_id)
    base_texte = extraire_texte_brut_paragraphe(paragraphe)
    morceaux: list[str] = []
    for frag in _fragments(etat, paragraphe_id):
        if frag["texte"] is None:
            morceaux.append(base_texte[frag["debut"]:frag["fin"]])
        else:
            morceaux.append(frag["texte"])
    return "".join(morceaux)


def textes_plats(etat: dict) -> list[str]:
    return [texte_paragraphe(etat, p.id) for p in etat["base"]]


# --- Modifications interactives ----------------------------------------------


def localiser(
    texte: str, fragment: str, contexte_avant: str = ""
) -> tuple[int, int] | None:
    """Localise un fragment sélectionné à l'écran dans le texte courant :
    ancre `contexte_avant + fragment`, sinon occurrence unique, sinon échec."""
    if not fragment or fragment not in texte:
        return None
    if contexte_avant:
        position = texte.find(contexte_avant + fragment)
        if position != -1:
            debut = position + len(contexte_avant)
            return debut, debut + len(fragment)
    occurrences = [m.start() for m in re.finditer(re.escape(fragment), texte)]
    if len(occurrences) == 1:
        return occurrences[0], occurrences[0] + len(fragment)
    if contexte_avant:
        candidats = [
            i for i in occurrences
            if texte[max(0, i - len(contexte_avant)):i] == contexte_avant
        ]
        if len(candidats) == 1:
            return candidats[0], candidats[0] + len(fragment)
    return None


def appliquer_modification(
    etat: dict, paragraphe_id: str, debut: int, fin: int, texte_ins: str
) -> None:
    """Splice d'une modification manuelle (alternative / embellissement) sur la
    BASE IMMUABLE : la sélection est donnée en coordonnées du texte COURANT,
    convertie en coordonnées BASE puis enregistrée comme PATCH indépendant —
    AUCUNE correction n'est décalée. Les Forme actives intersectées deviennent
    obsolètes (à réévaluer) ; Style/Technique restent ancrés sur la base (le
    rendu les projette sur la zone modifiée). Une sélection qui recouvre déjà
    un patch manuel est refusée (`ZoneDejaModifiee`)."""
    fragments = _fragments(etat, paragraphe_id)
    base_debut, base_fin = _convertir_vers_base(fragments, debut, fin)
    for patch in etat.get("patches", []):
        if (
            patch["paragraphe_id"] == paragraphe_id
            and base_debut < patch["fin"] and base_fin > patch["debut"]
        ):
            raise ZoneDejaModifiee(
                "La sélection recouvre une zone déjà modifiée — réévaluez le "
                "paragraphe ou choisissez un autre passage."
            )
    etat.setdefault("patches", []).append({
        "paragraphe_id": paragraphe_id,
        "debut": base_debut,
        "fin": base_fin,
        "texte": texte_ins,
    })
    for entree in etat["corrections"]:
        c = entree["correction"]
        if (
            c.paragraphe_id == paragraphe_id
            and entree["etat"] == "active"
            and c.phase == "forme"
            and base_debut < c.fin and base_fin > c.debut
        ):
            entree["etat"] = "obsolete"
            entree["motif"] = "Fragment modifié manuellement — réévaluez le paragraphe."
    if paragraphe_id not in etat.setdefault("modifies", []):
        etat["modifies"].append(paragraphe_id)


def remplacer_texte_paragraphe(etat: dict, paragraphe_id: str, nouveau_texte: str) -> bool:
    """Édition DIRECTE (jalon F3, décision 38) : remplace l'INTÉGRALITÉ du texte
    courant du paragraphe par `nouveau_texte` — un PATCH unique couvrant toute la
    base du paragraphe (jamais de splice + remappage des offsets). Tous les
    patches et corrections antérieurs du paragraphe sont retirés : ils se
    rapportaient à un texte qui n'existe plus (l'auteur a réécrit le paragraphe).
    Le paragraphe est marqué modifié à la main. Retourne False si rien ne change."""
    if nouveau_texte == texte_paragraphe(etat, paragraphe_id):
        return False
    paragraphe = _paragraphe(etat, paragraphe_id)
    ids_corrections = {
        e["correction"].id
        for e in etat["corrections"]
        if e["correction"].paragraphe_id == paragraphe_id
    }
    for cid in ids_corrections:
        etat.get("choix", {}).pop(cid, None)
    etat["patches"] = [
        p for p in etat.get("patches", []) if p["paragraphe_id"] != paragraphe_id
    ]
    etat["corrections"] = [
        e for e in etat["corrections"]
        if e["correction"].paragraphe_id != paragraphe_id
    ]
    etat.setdefault("patches", []).append({
        "paragraphe_id": paragraphe_id,
        "debut": 0,
        "fin": len(extraire_texte_brut_paragraphe(paragraphe)),
        "texte": nouveau_texte,
    })
    if paragraphe_id not in etat.setdefault("modifies", []):
        etat["modifies"].append(paragraphe_id)
    return True


def basculer_choix(etat: dict, correction_id: str, decision: str) -> bool:
    """Refuse ('original') ou ré-applique ('corrige') une correction Forme —
    un simple FILTRE : aucun remappage, la projection se recalcule. Retourne
    False si la correction n'existe pas ou n'est pas une Forme active."""
    entree = next(
        (e for e in etat["corrections"]
         if e["correction"].id == correction_id and e["etat"] == "active"),
        None,
    )
    if entree is None:
        return False
    c = entree["correction"]
    if c.phase != "forme":
        return False
    if decision == "original":
        etat.setdefault("choix", {})[c.id] = "original"
    elif decision == "corrige":
        etat.get("choix", {}).pop(c.id, None)
    else:
        return False
    return True


def remplacer_corrections_paragraphe(
    etat: dict, paragraphe_id: str, nouvelles: list[Correction]
) -> None:
    """Réévaluation : remplace toutes les corrections du paragraphe par les
    nouvelles (données en coordonnées du texte COURANT). Chaque correction est
    RÉ-ANCRÉE sur la base (jamais décalée ensuite) ; une correction non
    ancrable (zone manuelle coupée) est écartée avec un log."""
    # Les Forme APPLIQUÉES (actives, non refusées) deviennent des PATCHES
    # indépendants : la projection garde leur texte après la réévaluation
    # (l'ancien modèle gardait leur splice dans le texte courant — le workflow
    # est conservé, seule la représentation change).
    for entree in list(etat["corrections"]):
        c = entree["correction"]
        if (
            c.paragraphe_id == paragraphe_id
            and entree["etat"] == "active"
            and c.phase == "forme"
            and etat.get("choix", {}).get(c.id) != "original"
        ):
            etat.setdefault("patches", []).append({
                "paragraphe_id": paragraphe_id,
                "debut": c.debut,
                "fin": c.fin,
                "texte": c.correction,
            })
    # la projection COURANTE est figée AVANT le retrait : les nouvelles
    # corrections sont exprimées en coordonnées de ce texte courant
    fragments = _fragments(etat, paragraphe_id)
    etat["corrections"] = [
        e for e in etat["corrections"]
        if e["correction"].paragraphe_id != paragraphe_id
    ]
    ancrees: list[Correction] = []
    for c in nouvelles:
        try:
            base_debut, base_fin = _convertir_vers_base(
                fragments, c.debut, c.fin
            )
        except ZoneDejaModifiee:
            JOURNAL.warning(
                "Correction %s écartée après réévaluation (%s) : zone non ancrable sur la base",
                c.id, paragraphe_id,
            )
            continue
        ancrees.append(c.model_copy(update={"debut": base_debut, "fin": base_fin}))
    entrees = [{"correction": c, "etat": "active", "motif": None} for c in ancrees]
    etat["corrections"].extend(entrees)
    _resoudre_chevauchements_formes(etat, paragraphe_id)


# --- Extractions --------------------------------------------------------------


def vers_json(etat: dict) -> str:
    return json.dumps(
        {
            "modele": MODELE_ETAT,
            "base": [p.model_dump() for p in etat["base"]],
            "corrections": [
                {"correction": e["correction"].model_dump(), "etat": e["etat"], "motif": e["motif"]}
                for e in etat["corrections"]
            ],
            "choix": etat.get("choix", {}),
            "patches": etat.get("patches", []),
            "modifies": etat.get("modifies", []),
        },
        ensure_ascii=False,
    )


def depuis_json(brut: str) -> dict:
    donnees = json.loads(brut)
    return {
        "modele": MODELE_ETAT,
        "base": [ParagrapheRiche.model_validate(p) for p in donnees["base"]],
        "corrections": [
            {
                "correction": Correction.model_validate(e["correction"]),
                "etat": e.get("etat", "active"),
                "motif": e.get("motif"),
            }
            for e in donnees["corrections"]
        ],
        "choix": donnees.get("choix", {}),
        "patches": donnees.get("patches", []),
        "modifies": donnees.get("modifies", []),
    }


def est_ancien_format(donnees: dict) -> bool:
    """Un état antérieur au jalon R2 (texte courant muté dans `paragraphes`,
    corrections remappées) — à migrer via `migrer_ancien_format`."""
    return donnees.get("modele") != MODELE_ETAT or "base" not in donnees


def migrer_ancien_format(
    donnees_ancien: dict,
    base: list[ParagrapheRiche],
    corrections: list[Correction],
) -> dict:
    """Migration R2 d'un état `documents` antérieur : la BASE est reconstruite
    depuis le texte normalisé d'origine et les corrections depuis
    `corrections.data_json` (coordonnées base) ; les CHOIX/refus de l'auteur
    sont préservés par id ; les modifications manuelles (patches) de l'ancien
    état ne sont PAS rejouables proprement — elles sont abandonnées (décision
    de l'auteur, arbitrée au jalon R2)."""
    par_id = {e["correction"].get("id"): e for e in donnees_ancien.get("corrections", [])}
    ids_connus = {c.id for c in corrections}
    etat = {
        "modele": MODELE_ETAT,
        "base": [p.model_copy(deep=True) for p in base],
        "corrections": [
            {
                "correction": c,
                "etat": (par_id.get(c.id) or {}).get("etat", "active"),
                "motif": (par_id.get(c.id) or {}).get("motif"),
            }
            for c in corrections
        ],
        "choix": {
            cid: val for cid, val in (donnees_ancien.get("choix") or {}).items()
            if cid in ids_connus
        },
        "patches": [],
        "modifies": [],
    }
    for pid in {p.id for p in etat["base"]}:
        _resoudre_chevauchements_formes(etat, pid)
    return etat


# --- Outils internes -----------------------------------------------------------


def _paragraphe(etat: dict, paragraphe_id: str) -> ParagrapheRiche:
    for p in etat["base"]:
        if p.id == paragraphe_id:
            return p
    raise ValueError(f"Paragraphe {paragraphe_id} inconnu dans l'état courant")


def _fusionner_runs(runs: list[RunFormat]) -> list[RunFormat]:
    """Fusionne les runs adjacents de mêmes attributs (limite la fragmentation)."""
    sortie: list[RunFormat] = []
    for run in runs:
        if not run.texte:
            continue
        precedent = sortie[-1] if sortie else None
        if (
            precedent is not None
            and precedent.gras == run.gras
            and precedent.italique == run.italique
            and precedent.souligne == run.souligne
        ):
            sortie[-1] = RunFormat(
                texte=precedent.texte + run.texte,
                gras=run.gras, italique=run.italique, souligne=run.souligne,
            )
        else:
            sortie.append(run)
    return sortie