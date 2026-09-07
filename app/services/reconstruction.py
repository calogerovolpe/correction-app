"""Reconstruction de l'état courant du texte — atelier E5 (jalon J2.5, spec §8).

Règle de mission : la version validée ou soumise est EXACTEMENT le texte
affiché à l'écran au moment du clic. L'état courant est donc matérialisé
(persistance : table `documents`) :
- `paragraphes` : le texte COURANT (runs riches ; évolue à chaque modification) ;
- `corrections` : les corrections, TOUJOURS exprimées dans les coordonnées du
  texte courant (remappées après chaque modification). Chaque entrée porte
  `etat` ('active' | 'obsolete') et `motif` ;
- `choix` : refus explicites de corrections Forme ({id: "original"}) ;
- `modifies` : identifiants des paragraphes modifiés à la main (le bouton
  « Réévaluer » leur est proposé).

Sémantique :
- les corrections Forme sont APPLIQUÉES PAR DÉFAUT (l'écran montre l'original
  barré + la correction insérée) ; refuser = restituer l'original à sa place ;
- toute modification est une splice de runs : le fragment courant [debut, fin)
  est remplacé en préservant le formatage (gras/italique/souligné du premier
  run remplacé), puis les corrections du paragraphe sont remappées de façon
  DÉTERMINISTE (jamais de recherche floue) :
    * entièrement après la zone → décalées de `delta` ;
    * intersectant la zone → couvrent le texte de remplacement tout entier
      (Style/Technique) ou deviennent obsolètes (Forme : le fragment qu'elle
      décrit n'existe plus — le paragraphe est à réévaluer) ;
    * entièrement avant → inchangées ;
- les corrections Forme qui se chevauchent entre elles : la première garde la
  main, les suivantes sont obsolètes (« chevauche une autre correction »).
"""

import json
import re

from app.models import CorrectionFusionnee
from app.services.texte_riche import (
    ParagrapheRiche,
    RunFormat,
    decouper_runs_par_intervalle,
    extraire_texte_brut_paragraphe,
)


# --- Fabrique de l'état ------------------------------------------------------


def etat_initial(
    fusion: list[CorrectionFusionnee], paragraphes: list[ParagrapheRiche]
) -> dict:
    """État courant initial : corrections Forme appliquées par défaut."""
    etat: dict = {
        "paragraphes": [p.model_copy(deep=True) for p in paragraphes],
        "corrections": [
            {"fusion": f, "etat": "active", "motif": None} for f in fusion
        ],
        "choix": {},
        "modifies": [],
    }
    for pid in {p.id for p in etat["paragraphes"]}:
        entrees_pid = [
            e for e in etat["corrections"]
            if e["fusion"].correction.paragraphe_id == pid
        ]
        _appliquer_formes(etat, entrees_pid, _paragraphe(etat, pid))
    return etat


def _appliquer_formes(etat: dict, entrees_pid: list[dict], paragraphe: ParagrapheRiche) -> None:
    """Applique les corrections Forme actives (par offsets décroissants), puis
    remappe TOUTES les corrections du paragraphe sur le texte courant."""
    formes = [e for e in entrees_pid if e["fusion"].correction.phase == "forme"]
    if not formes:
        return
    resolues: list[dict] = []
    for entree in sorted(
        formes, key=lambda e: (e["fusion"].correction.debut, e["fusion"].correction.fin)
    ):
        c = entree["fusion"].correction
        if any(
            c.debut < f and c.fin > d
            for d, f in ((r["fusion"].correction.debut, r["fusion"].correction.fin) for r in resolues)
        ):
            entree["etat"] = "obsolete"
            entree["motif"] = "Chevauche une autre correction Forme — non appliquée."
        else:
            resolues.append(entree)
    if not resolues:
        return
    splices: list[tuple[int, int, int]] = []
    for entree in sorted(resolues, key=lambda e: e["fusion"].correction.debut, reverse=True):
        c = entree["fusion"].correction
        paragraphe.runs = _remplacer_runs(paragraphe.runs, c.debut, c.fin, c.correction)
        splices.append((c.debut, c.fin, len(c.correction)))
    for entree in entrees_pid:
        c = entree["fusion"].correction
        nouveau_debut, nouveau_fin = _recalculer(splices, c.debut, c.fin)
        if (nouveau_debut, nouveau_fin) != (c.debut, c.fin):
            _maj_correction(entree, debut=nouveau_debut, fin=nouveau_fin)


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
    """Splice d'une modification manuelle (alternative / embellissement) +
    remappage : les Formes intersectées deviennent obsolètes, Style/Technique
    couvrent le texte de remplacement, les suivantes sont décalées."""
    paragraphe = _paragraphe(etat, paragraphe_id)
    paragraphe.runs = _remplacer_runs(paragraphe.runs, debut, fin, texte_ins)
    _remapper_apres_splice(
        etat["corrections"], paragraphe_id, debut, fin, len(texte_ins),
        forme_devient_obsolete=True,
    )
    if paragraphe_id not in etat.setdefault("modifies", []):
        etat["modifies"].append(paragraphe_id)


def basculer_choix(etat: dict, correction_id: str, decision: str) -> bool:
    """Refuse ('original') ou ré-applique ('corrige') une correction Forme.
    Retourne False si la correction n'existe pas ou n'est pas une Forme active."""
    entree = next(
        (e for e in etat["corrections"]
         if e["fusion"].correction.id == correction_id and e["etat"] == "active"),
        None,
    )
    if entree is None:
        return False
    c = entree["fusion"].correction
    if c.phase != "forme":
        return False
    ins = c.original if decision == "original" else c.correction
    paragraphe = _paragraphe(etat, c.paragraphe_id)
    paragraphe.runs = _remplacer_runs(paragraphe.runs, c.debut, c.fin, ins)
    _remapper_apres_splice(
        etat["corrections"], c.paragraphe_id, c.debut, c.fin, len(ins),
        forme_devient_obsolete=False, id_exempt=c.id,
    )
    if decision == "original":
        etat.setdefault("choix", {})[c.id] = "original"
    else:
        etat.get("choix", {}).pop(c.id, None)
    return True


def remplacer_corrections_paragraphe(
    etat: dict, paragraphe_id: str, nouvelles: list[CorrectionFusionnee]
) -> None:
    """Réévaluation : remplace toutes les corrections du paragraphe par les
    nouvelles (offsets donnés dans le texte courant), puis applique les
    nouvelles Formes par défaut (même mécanique que l'état initial)."""
    etat["corrections"] = [
        e for e in etat["corrections"]
        if e["fusion"].correction.paragraphe_id != paragraphe_id
    ]
    entrees = [{"fusion": f, "etat": "active", "motif": None} for f in nouvelles]
    etat["corrections"].extend(entrees)
    _appliquer_formes(etat, entrees, _paragraphe(etat, paragraphe_id))


# --- Extractions --------------------------------------------------------------


def texte_paragraphe(etat: dict, paragraphe_id: str) -> str:
    return extraire_texte_brut_paragraphe(_paragraphe(etat, paragraphe_id))


def textes_plats(etat: dict) -> list[str]:
    return [extraire_texte_brut_paragraphe(p) for p in etat["paragraphes"]]


def vers_json(etat: dict) -> str:
    return json.dumps(
        {
            "paragraphes": [p.model_dump() for p in etat["paragraphes"]],
            "corrections": [
                {"fusion": e["fusion"].model_dump(), "etat": e["etat"], "motif": e["motif"]}
                for e in etat["corrections"]
            ],
            "choix": etat.get("choix", {}),
            "modifies": etat.get("modifies", []),
        },
        ensure_ascii=False,
    )


def depuis_json(brut: str) -> dict:
    donnees = json.loads(brut)
    return {
        "paragraphes": [ParagrapheRiche.model_validate(p) for p in donnees["paragraphes"]],
        "corrections": [
            {
                "fusion": CorrectionFusionnee.model_validate(e["fusion"]),
                "etat": e.get("etat", "active"),
                "motif": e.get("motif"),
            }
            for e in donnees["corrections"]
        ],
        "choix": donnees.get("choix", {}),
        "modifies": donnees.get("modifies", []),
    }


# --- Outils internes -----------------------------------------------------------


def _paragraphe(etat: dict, paragraphe_id: str) -> ParagrapheRiche:
    for p in etat["paragraphes"]:
        if p.id == paragraphe_id:
            return p
    raise ValueError(f"Paragraphe {paragraphe_id} inconnu dans l'état courant")


def _maj_correction(entree: dict, **champs) -> None:
    fusion = entree["fusion"]
    entree["fusion"] = CorrectionFusionnee(
        correction=fusion.correction.model_copy(update=champs),
        embellissement_migre=fusion.embellissement_migre,
    )


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


def _remplacer_runs(
    runs: list[RunFormat], debut: int, fin: int, nouveau_texte: str
) -> list[RunFormat]:
    """Remplace [debut, fin) par `nouveau_texte` en préservant le formatage
    (flags du premier run couvert)."""
    if fin <= debut:
        return _fusionner_runs(runs)
    avant, couverts, apres = decouper_runs_par_intervalle(runs, debut, fin)
    if nouveau_texte:
        premier = couverts[0] if couverts else None
        insere = RunFormat(
            texte=nouveau_texte,
            gras=premier.gras if premier else False,
            italique=premier.italique if premier else False,
            souligne=premier.souligne if premier else False,
        )
        runs_nouveaux = avant + [insere] + apres
    else:
        runs_nouveaux = avant + apres
    return _fusionner_runs(runs_nouveaux)


def _remapper_apres_splice(
    entrees: list[dict],
    paragraphe_id: str,
    debut: int,
    fin: int,
    longueur: int,
    forme_devient_obsolete: bool,
    id_exempt: str | None = None,
) -> None:
    """Remappage déterministe des corrections d'un paragraphe après une splice."""
    delta = longueur - (fin - debut)
    for entree in entrees:
        c = entree["fusion"].correction
        if c.paragraphe_id != paragraphe_id or entree["etat"] != "active":
            continue
        if id_exempt is not None and c.id == id_exempt:
            _maj_correction(entree, debut=debut, fin=debut + longueur)
        elif c.fin <= debut:
            continue  # entièrement avant : inchangée
        elif c.debut >= fin:
            _maj_correction(entree, debut=c.debut + delta, fin=c.fin + delta)
        else:  # intersecte la zone
            if forme_devient_obsolete and c.phase == "forme":
                entree["etat"] = "obsolete"
                entree["motif"] = (
                    "Fragment modifié manuellement — réévaluez le paragraphe."
                )
            else:
                _maj_correction(entree, debut=debut, fin=debut + longueur)


def _recalculer(
    splices: list[tuple[int, int, int]], a: int, b: int
) -> tuple[int, int]:
    """Position courante d'un intervalle d'origine [a, b) : s'il intersecte une
    splice → il couvre le texte de remplacement ; sinon → décalé uniquement."""
    for d, f, longueur in splices:
        if a < f and b > d:
            cs = d + sum(l - (f2 - d2) for d2, f2, l in splices if f2 <= d)
            return cs, cs + longueur
    decal = sum(l - (f - d) for d, f, l in splices if f <= a)
    return a + decal, b + decal

