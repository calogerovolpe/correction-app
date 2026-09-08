"""API JSON — /api/v1 (jalons F1 : Accueil & projets E1 ; F2 : Soumission E3
+ suivi E4).

Réutilise les services purs et l'accès SQL existants (`app.db`) — aucune
logique métier dupliquée. Les routes Jinja2 de `app.routes.web` restent
conservées jusqu'à la bascule (F5) ; ce routeur est la cible du frontend
Svelte.

Comportement métier (spec §8.2-E1/E3/E4, §11 décisions 16 et 37) :
- création (le premier projet d'un espace vierge devient automatiquement actif) ;
- activation par UPSERT du pointeur `parametres.projet_actif` (un seul actif) ;
- suppression totale en cascade, projet actif protégé (le trigger SQL
  `trg_projet_actif_restrict` reste la garantie ultime derrière le 409) ;
- F2 : soumission d'un texte (E3) et suivi asynchrone du job (E4) — même
  moteur de jobs que le POST /analyses Jinja2 (spec §2.3/§7) : la tâche
  `service_analyse.executer(id)` est référencée dans `_TACHES`, le pipeline
  LLM (fail-fast, Option B, « liste vide = jamais une panne ») reste INTACT.
"""

import asyncio
import json
from typing import Annotated, Literal, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app import db
from app.config import settings
from app.routes.web import (
    _TACHES,
    _analyse,
    _dernieres_options,
    _normaliser_prefil,
    _nouvel_id,
    _projet_actif,
    _projet_actif_id,
)
from app.services import analyse as service_analyse
from app.services import atelier as service_atelier
from app.services.atelier import ErreurAtelier
from app.services.chaine import numero_attendu

router = APIRouter(prefix="/api/v1")


class TitreProjet(BaseModel):
    titre: str = Field(min_length=1, max_length=200)


class Projet(BaseModel):
    projet_id: str
    titre: str
    actif: bool
    chain_status: str
    current_chapter_num: int | None
    last_chapter_title: str | None
    created_at: str


class ListeProjets(BaseModel):
    projets: list[Projet]


class AnalyseLigne(BaseModel):
    id: int
    statut: str
    categorie: str | None
    extrait: str
    cree_a: str


class ListeAnalyses(BaseModel):
    analyses: list[AnalyseLigne]


# --- F2 : Soumission E3 + suivi E4 ----------------------------------------------------


class SoumissionAnalyse(BaseModel):
    """Corps du POST /api/v1/analyses — équivalent JSON du formulaire E3
    (champ caché `phases` inclus). `phases` absent ou nul → pré-sélection par
    catégorie (`analyse.phases_actives`) ; fourni avec au moins une case vraie
    → dérogation à la matrice."""

    texte: str
    categorie: str = "chapitre"
    numero_chapitre: float | None = None
    avec_codex: bool = False
    phases: dict[str, bool] | None = None


class ResultatAnalyse(BaseModel):
    """Synthèse lecture seule de l'état final d'une analyse `terminee`.
    Comptée par phase depuis `corrections.data_json` (stockage PAR PHASE,
    R1-b). Le payload complet de l'atelier arrivera au jalon F3 — ce contrat
    est pensé pour s'étendre sans rupture."""

    nb_corrections: int
    par_phase: dict[str, int]


class AnalyseSuivi(BaseModel):
    """État d'une analyse côté client : statut explicite (en_attente → en_cours
    → terminee | echec | rejetee), étape courante, message d'erreur (gabarits
    fail-fast / Option B) — jamais de statut fantôme."""

    id: int
    statut: str
    etape: str | None = None
    erreur: str | None = None
    categorie: str | None = None
    cree_a: str | None = None
    fini_a: str | None = None
    resultat: ResultatAnalyse | None = None


class PrefilPhases(BaseModel):
    forme: bool
    style: bool
    technique: bool


class PrefilSoumission(BaseModel):
    categorie: str
    phases: PrefilPhases


class PreparerSoumission(BaseModel):
    """État de préparation de E3 : projet actif, numéro attendu (N+1), dernières
    configurations mémorisées (J2.5) et garde-fou de taille (source unique du
    compteur 30 000 caractères)."""

    projet: Projet | None
    numero_attendu: int | float
    prefil: PrefilSoumission
    max_caracteres: int


def _choix_phases_payload(phases: dict[str, bool] | None) -> dict[str, bool | None]:
    """Décode le champ `phases` (dict booléens) du corps JSON — contrat
    IDENTIQUE au champ caché `phases` du formulaire E3 (`web.py::_choix_phases`) :
    {} si absent → pré-sélection par catégorie ; les cases présentes sont
    filtrees sur les trois phases (Forme, Style, Technique)."""

    if not phases:
        return {}
    return {
        phase: bool(phases[phase])
        for phase in ("forme", "style", "technique")
        if phase in phases
    }


async def _synthese_resultat(analyse_id: int) -> ResultatAnalyse:
    """Compte les corrections par phase depuis `corrections.data_json`
    (dict PAR PHASE, R1-b) — lecture seule, jamais de mutation."""

    lignes = await db.interroger(
        "SELECT data_json FROM corrections WHERE analyse_id = ?", (analyse_id,)
    )
    par_phase: dict[str, int] = {}
    if lignes:
        donnees = json.loads(lignes[0]["data_json"] or "{}")
        for phase, corrections in donnees.items():
            par_phase[phase] = len(corrections)
    return ResultatAnalyse(
        nb_corrections=sum(par_phase.values()),
        par_phase=par_phase,
    )


def _serialiser_suivi(analyse: dict, resultat: ResultatAnalyse | None) -> AnalyseSuivi:
    return AnalyseSuivi(
        id=analyse["id"],
        statut=analyse["statut"],
        etape=analyse.get("etape"),
        erreur=analyse.get("erreur"),
        categorie=analyse.get("categorie"),
        cree_a=analyse.get("cree_a"),
        fini_a=analyse.get("fini_a"),
        resultat=resultat,
    )


def _serialiser_projet(ligne: dict, actif_id: str | None) -> Projet:
    """Sérialise une ligne `projets` en réponse API (drapeau `actif` calculé)."""
    return Projet(
        projet_id=ligne["projet_id"],
        titre=ligne["titre"],
        actif=ligne["projet_id"] == actif_id,
        chain_status=ligne["chain_status"],
        current_chapter_num=ligne["current_chapter_num"],
        last_chapter_title=ligne["last_chapter_title"],
        created_at=ligne["created_at"],
    )


@router.get("/projets", response_model=ListeProjets)
async def lister_projets() -> ListeProjets:
    """Liste des projets (tri : plus récents d'abord), avec drapeau `actif`."""
    actif_id = await _projet_actif_id()
    lignes = await db.interroger(
        "SELECT * FROM projets ORDER BY created_at DESC, projet_id DESC"
    )
    return ListeProjets(projets=[_serialiser_projet(l, actif_id) for l in lignes])


@router.post("/projets", response_model=Projet, status_code=201)
async def creer_projet(payload: TitreProjet) -> Projet:
    """Crée un projet (titre obligatoire, non vide). Le premier projet d'un
    espace vierge devient automatiquement le projet actif (spec §11 déc. 16)."""
    titre = payload.titre.strip()
    if not titre:
        raise HTTPException(status_code=400, detail="Le titre du projet est vide.")
    projet_id = _nouvel_id()
    await db.executer(
        "INSERT INTO projets (projet_id, titre) VALUES (?, ?)", (projet_id, titre)
    )
    if await _projet_actif_id() is None:
        await db.executer(
            "INSERT INTO parametres (cle, valeur) VALUES ('projet_actif', ?)",
            (projet_id,),
        )
    actif_id = await _projet_actif_id()
    lignes = await db.interroger(
        "SELECT * FROM projets WHERE projet_id = ?", (projet_id,)
    )
    return _serialiser_projet(lignes[0], actif_id)


@router.post("/projets/{projet_id}/activer", status_code=204)
async def activer_projet(projet_id: str) -> None:
    """Active un projet : UPSERT du pointeur `parametres.projet_actif`
    (un seul projet actif à la fois)."""
    lignes = await db.interroger(
        "SELECT 1 FROM projets WHERE projet_id = ?", (projet_id,)
    )
    if not lignes:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    await db.executer(
        "INSERT INTO parametres (cle, valeur) VALUES ('projet_actif', ?) "
        "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
        (projet_id,),
    )


@router.delete("/projets/{projet_id}", status_code=204)
async def supprimer_projet(projet_id: str) -> None:
    """Supprime un projet non actif ; la suppression totale en cascade est
    portée par le schéma (ON DELETE CASCADE sur toutes les tables filles).
    Projet actif : refus explicite 409 en amont du trigger SQL."""
    lignes = await db.interroger(
        "SELECT 1 FROM projets WHERE projet_id = ?", (projet_id,)
    )
    if not lignes:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    if projet_id == await _projet_actif_id():
        raise HTTPException(
            status_code=409,
            detail="Le projet actif ne peut pas être supprimé — activez d'abord un autre projet.",
        )
    await db.executer("DELETE FROM projets WHERE projet_id = ?", (projet_id,))


@router.get("/analyses", response_model=ListeAnalyses)
async def analyses_recentes() -> ListeAnalyses:
    """Analyses récentes (10 dernières, lecture seule) pour l'accueil E1."""
    lignes = await db.interroger(
        "SELECT id, statut, categorie, substr(texte_source, 1, 60) AS extrait, cree_a "
        "FROM analyses ORDER BY id DESC LIMIT 10"
    )
    return ListeAnalyses(analyses=[AnalyseLigne(**l) for l in lignes])


@router.get("/soumission", response_model=PreparerSoumission)
async def preparer_soumission() -> PreparerSoumission:
    """État de préparation de E3 (jalon F2) : projet actif, numéro N+1 attendu,
    dernières configurations mémorisées (J2.5) et garde-fou de taille."""
    projet = await _projet_actif()
    actif_id = await _projet_actif_id()
    attendu = numero_attendu(projet) if projet else 0.0
    prefil = _normaliser_prefil(await _dernieres_options())
    return PreparerSoumission(
        projet=_serialiser_projet(projet, actif_id) if projet else None,
        numero_attendu=int(attendu) if attendu == int(attendu) else attendu,
        prefil=PrefilSoumission(
            categorie=prefil["categorie"],
            phases=PrefilPhases(
                forme=prefil["forme"],
                style=prefil["style"],
                technique=prefil["technique"],
            ),
        ),
        max_caracteres=settings.max_caracteres,
    )


@router.post("/analyses", response_model=AnalyseSuivi, status_code=201)
async def soumettre_analyse_api(payload: SoumissionAnalyse) -> AnalyseSuivi:
    """Soumission d'un texte (E3) — équivalent JSON du POST /analyses Jinja2.

    Refus explicites 400 (texte vide, dépassement max_caracteres — jamais de
    troncature silencieuse, aucune phase cochée, aucun projet actif) puis
    création du job asynchrone réutilisant le moteur existant (spec §2.3/§7) :
    `analyse.executer(id)` lancé en tâche et référencé dans `_TACHES` — le
    pipeline LLM n'est PAS modifié."""

    projet = await _projet_actif()
    erreur = None
    if projet is None:
        erreur = "Aucun projet actif : créez d'abord un projet (roman) sur la page d'accueil."
    elif not payload.texte.strip():
        erreur = "Le texte soumis est vide."
    elif len(payload.texte) > settings.max_caracteres:
        erreur = (
            f"Texte de {len(payload.texte)} caractères — la limite est de "
            f"{settings.max_caracteres}. Refus explicite : aucune troncature "
            "silencieuse du contexte (v6 §2.3)."
        )
    else:
        choix = _choix_phases_payload(payload.phases)
        if choix and not any(choix.values()):
            erreur = "Sélectionnez au moins un type de correction (Forme, Style ou Technique)."
    if erreur:
        raise HTTPException(status_code=400, detail=erreur)

    cat_choisie = (
        payload.categorie
        if payload.categorie in ("chapitre", "passage", "extrait")
        else "chapitre"
    )
    num_chap = None
    if cat_choisie == "chapitre" and payload.numero_chapitre is not None:
        try:
            num_chap = float(payload.numero_chapitre)
        except (ValueError, TypeError):
            num_chap = None

    choix = _choix_phases_payload(payload.phases)
    options = {
        "categorie": cat_choisie,
        "numero_chapitre": num_chap,
        "avec_codex": bool(payload.avec_codex) if cat_choisie == "chapitre" else False,
        "forme": choix.get("forme"),
        "style": choix.get("style"),
        "technique": choix.get("technique"),
    }
    # Mémoire des configurations : pré-remplissage de E3 pour le prochain texte (J2.5)
    await db.executer(
        "INSERT INTO parametres (cle, valeur) VALUES ('dernieres_options', ?) "
        "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
        (
            json.dumps(
                {
                    "categorie": cat_choisie,
                    "phases": {k: bool(v) for k, v in choix.items()},
                },
                ensure_ascii=False,
            ),
        ),
    )
    identifiant, _ = await db.executer(
        "INSERT INTO analyses (projet_id, texte_source, options_json) VALUES (?, ?, ?)",
        (projet["projet_id"], payload.texte, json.dumps(options, ensure_ascii=False)),
    )
    tache = asyncio.create_task(service_analyse.executer(identifiant))
    _TACHES.add(tache)
    tache.add_done_callback(_TACHES.discard)

    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (identifiant,))
    return _serialiser_suivi(lignes[0], None)


@router.get("/analyses/{analyse_id}", response_model=AnalyseSuivi)
async def statut_analyse(analyse_id: int) -> AnalyseSuivi:
    """Statut/suivi d'une analyse (E4), lecture pure pour le polling : statut
    explicite, étape courante, erreur (gabarits fail-fast / Option B). Quand le
    job est `terminee`, une synthèse lecture seule du résultat est jointe
    (`resultat`) — étendue par le payload complet de l'atelier au jalon F3."""

    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (analyse_id,))
    if not lignes:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")
    analyse = lignes[0]
    resultat = (
        await _synthese_resultat(analyse_id)
        if analyse["statut"] == "terminee"
        else None
    )
    return _serialiser_suivi(analyse, resultat)


# --- F3 : Atelier E5 (API JSON) ------------------------------------------------
# La logique métier est partagée avec `app/services/atelier.py` (aucune
# duplication) ; ces routes déléguent puis sérialisent le document annoté.


class SegmentTexte(BaseModel):
    type: Literal["texte"]
    texte: str
    gras: bool = False
    italique: bool = False
    souligne: bool = False
    classes: str = ""
    groupe: str | None = None


class SegmentForme(BaseModel):
    """Segment de correction Forme : original barré (`del`) + correction insérée
    (`ins`). `del` étant un mot-clé Python, le champ est `del_` avec un alias
    sérialisation `del` (contrat JSON à l'identique de `rendu.py`)."""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["forme"]
    groupe: str
    del_: str = Field(alias="del", serialization_alias="del")
    ins: str
    gras: bool = False
    italique: bool = False
    souligne: bool = False
    classes: str = ""


SegmentAnnote = Annotated[Union[SegmentTexte, SegmentForme], Field(discriminator="type")]


class ParagrapheAnnote(BaseModel):
    id: str
    edite: bool = False
    segments: list[SegmentAnnote]


class CorrectionBarre(BaseModel):
    """Entrée de la barre latérale (détails d'une correction cliquée)."""

    id: str
    groupe: str
    phase: str
    type: str
    paragraphe_id: str
    debut: int
    fin: int
    original: str
    correction: str
    explication: str
    regle: str = ""
    titre: str
    etat: str
    motif: str | None = None
    decision: str | None = None


class DocumentAnnote(BaseModel):
    paragraphes: list[ParagrapheAnnote]
    nb_masques: int
    corrections_barre: list[CorrectionBarre]


class EtatAtelier(BaseModel):
    """Contrat GET /api/v1/analyses/{id}/atelier (F3) : le document annoté et
    les métadonnées dont le frontend Svelte a besoin pour E5."""

    id: int
    statut: str
    categorie: str | None = None
    onglet: str
    est_chapitre: bool
    a_embellissement: bool
    nb_corrections: int
    compteurs: dict[str, int]
    document: DocumentAnnote


class DecisionForme(BaseModel):
    correction_id: str
    decision: Literal["corrige", "original"]


class ModificationSelection(BaseModel):
    paragraphe_id: str
    fragment: str
    texte: str
    contexte: str = ""


class EditionParagraphe(BaseModel):
    paragraphe_id: str
    # `texte` optionnel : requis pour l'édition directe, ignoré pour la
    # réévaluation d'un paragraphe (cible identifiée par `paragraphe_id` seul).
    texte: str = ""


class DemandeSuggestion(BaseModel):
    fragment: str
    paragraphe_texte: str
    contexte: str = ""


async def _etat_atelier_payload(analyse, etat, onglet: str = "tout") -> EtatAtelier:
    """Sérialise le document annoté (service partagé) en contrat JSON F3."""
    contexte = service_atelier.contexte_resultat(analyse, etat, onglet=onglet)
    return EtatAtelier(
        id=analyse["id"],
        statut=analyse["statut"],
        categorie=analyse.get("categorie"),
        onglet=contexte["onglet"],
        est_chapitre=contexte["est_chapitre"],
        a_embellissement=contexte["a_embellissement"],
        nb_corrections=contexte["nb_corrections"],
        compteurs=contexte["compteurs"],
        document=DocumentAnnote.model_validate(contexte["document"]),
    )


async def _demander_atelier(analyse_id: int, onglet: str = "tout") -> EtatAtelier:
    """Charge l'analyse terminée + son état atelier, ou lève le statut adapté."""
    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (analyse_id,))
    if not lignes:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")
    analyse = lignes[0]
    if analyse["statut"] != "terminee":
        raise HTTPException(status_code=400, detail="Analyse non terminée.")
    etat = await service_atelier.charger_etat(analyse)
    return await _etat_atelier_payload(analyse, etat, onglet)


@router.get("/analyses/{analyse_id}/atelier", response_model=EtatAtelier)
async def etat_atelier(analyse_id: int, onglet: str = "tout") -> EtatAtelier:
    """Document annoté de l'atelier E5 (F3) : base immuable + annotations
    projetées selon l'onglet (tout | forme | style | technique | embellissement).
    Lecture pure — ne déclenche JAMAIS l'analyse (jamais de statut fantôme)."""
    return await _demander_atelier(analyse_id, onglet)


@router.post("/analyses/{analyse_id}/choix-forme", response_model=EtatAtelier)
async def api_choix_forme(analyse_id: int, payload: DecisionForme) -> EtatAtelier:
    """Accepte ('corrige') ou refuse ('original') une correction Forme : un
    simple FILTRE (R2) — la projection se recalcule, aucun remappage."""
    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (analyse_id,))
    if not lignes:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")
    analyse = lignes[0]
    if analyse["statut"] != "terminee":
        raise HTTPException(status_code=400, detail="Analyse non terminée.")
    etat = await service_atelier.charger_etat(analyse)
    try:
        await service_atelier.choisir_forme(analyse, etat, payload.correction_id, payload.decision)
    except ErreurAtelier as erreur:
        raise HTTPException(status_code=erreur.statut, detail=str(erreur)) from erreur
    return await _etat_atelier_payload(analyse, etat)


@router.post("/analyses/{analyse_id}/appliquer-alternative", response_model=EtatAtelier)
async def api_appliquer_alternative(
    analyse_id: int, payload: ModificationSelection
) -> EtatAtelier:
    """Applique l'alternative choisie par l'auteur (clic droit sur sélection)."""
    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (analyse_id,))
    if not lignes:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")
    analyse = lignes[0]
    if analyse["statut"] != "terminee":
        raise HTTPException(status_code=400, detail="Analyse non terminée.")
    etat = await service_atelier.charger_etat(analyse)
    try:
        await service_atelier.appliquer_alternative(
            analyse, etat, payload.paragraphe_id, payload.fragment, payload.texte, payload.contexte
        )
    except ErreurAtelier as erreur:
        raise HTTPException(status_code=erreur.statut, detail=str(erreur)) from erreur
    return await _etat_atelier_payload(analyse, etat)


@router.post("/analyses/{analyse_id}/editer", response_model=EtatAtelier)
async def api_editer_paragraphe(analyse_id: int, payload: EditionParagraphe) -> EtatAtelier:
    """Édition DIRECTE sans IA temps réel (UX4, décision 38) : remplace le texte
    courant affiché du paragraphe (patch ancré base) ; « ↻ Re-corriger » relance
    le pipeline ensuite."""
    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (analyse_id,))
    if not lignes:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")
    analyse = lignes[0]
    if analyse["statut"] != "terminee":
        raise HTTPException(status_code=400, detail="Analyse non terminée.")
    etat = await service_atelier.charger_etat(analyse)
    try:
        await service_atelier.editer_paragraphe(analyse, etat, payload.paragraphe_id, payload.texte)
    except ErreurAtelier as erreur:
        raise HTTPException(status_code=erreur.statut, detail=str(erreur)) from erreur
    return await _etat_atelier_payload(analyse, etat)


@router.post("/analyses/{analyse_id}/reevaluer", response_model=EtatAtelier)
async def api_reevaluer(
    analyse_id: int, payload: EditionParagraphe
) -> EtatAtelier:
    """Réévaluation manuelle des corrections d'un paragraphe (bouton « ↻ »)."""
    les_lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (analyse_id,))
    if not les_lignes:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")
    analyse = les_lignes[0]
    if analyse["statut"] != "terminee":
        raise HTTPException(status_code=400, detail="Analyse non terminée.")
    paragraphe_id = payload.paragraphe_id
    etat = await service_atelier.charger_etat(analyse)
    try:
        await service_atelier.reevaluer(analyse, etat, paragraphe_id)
    except ErreurAtelier as erreur:
        raise HTTPException(status_code=erreur.statut, detail=str(erreur)) from erreur
    return await _etat_atelier_payload(analyse, etat)


@router.post("/analyses/{analyse_id}/nouvelle-version")
async def api_nouvelle_version(analyse_id: int) -> dict:
    """Soumet une NOUVELLE analyse dont le texte source est EXACTEMENT le texte
    courant (le texte affiché, avec les choix et modifications de l'auteur). Le
    job asynchrone est lancé ; le frontend navigue vers le suivi du nouvel id."""
    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (analyse_id,))
    if not lignes:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")
    analyse = lignes[0]
    if analyse["statut"] != "terminee":
        raise HTTPException(status_code=400, detail="Analyse non terminée.")
    try:
        nouvel_id = await service_atelier.nouvelle_version(analyse)
    except Exception as erreur:  # noqa: BLE001 — jamais de statut fantôme
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la nouvelle version : {erreur}",
        ) from erreur
    return {"nouvel_id": nouvel_id}


@router.post("/analyses/{analyse_id}/valider")
async def api_valider(analyse_id: int) -> dict:
    """Valide officiellement le chapitre : enregistre dans `chapitres` le TEXTE
    AFFICHÉ au moment du clic (qu'il soit corrigé ou non), avec son hash
    SHA-256, après un backup natif SQLite ; « dernier validé gagne » fait
    avancer la chaîne N+1. Réservé aux Chapitres (Passage/Extrait : 400)."""
    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (analyse_id,))
    if not lignes:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")
    analyse = lignes[0]
    try:
        resum = await service_atelier.valider(analyse)
    except ErreurAtelier as erreur:
        raise HTTPException(status_code=erreur.statut, detail=str(erreur)) from erreur
    return {"ok": True, **resum}


@router.post("/embellir")
async def api_embellir_json(demande: DemandeSuggestion) -> dict:
    """Propose une réécriture embellie du passage sélectionné (contexte pris en
    compte). Aucun état modifié : l'auteur voit puis applique ou annule."""
    return await service_atelier.suggerer_embellissement(
        demande.fragment, demande.paragraphe_texte, demande.contexte
    )


@router.post("/alternatives")
async def api_alternatives_json(demande: DemandeSuggestion) -> dict:
    """Propose des alternatives (synonymes, champ lexical) cohérentes avec le
    contexte du passage sélectionné (clic droit). Aucun état modifié."""
    return await service_atelier.suggerer_alternatives(
        demande.fragment, demande.paragraphe_texte
    )


@router.post("/analyses/{analyse_id}/appliquer-embellissement", response_model=EtatAtelier)
async def api_appliquer_embellissement(
    analyse_id: int, payload: ModificationSelection
) -> EtatAtelier:
    """Applique l'embellissement choisi, PUIS réévalue les corrections du
    paragraphe. Zéro surprise : si la réévaluation échoue, RIEN n'est appliqué
    (aucun état partiel)."""
    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (analyse_id,))
    if not lignes:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")
    analyse = lignes[0]
    if analyse["statut"] != "terminee":
        raise HTTPException(status_code=400, detail="Analyse non terminée.")
    etat = await service_atelier.charger_etat(analyse)
    try:
        await service_atelier.appliquer_embellissement(
            analyse, etat, payload.paragraphe_id, payload.fragment, payload.texte, payload.contexte
        )
    except ErreurAtelier as erreur:
        raise HTTPException(status_code=erreur.statut, detail=str(erreur)) from erreur
    return await _etat_atelier_payload(analyse, etat)