"""Écran E5 — atelier de relecture et workflow de fin de chapitre (jalon J2.5 → F3).

Depuis le jalon F3, la logique métier vit dans `app/services/atelier.py`
(partagée avec l'API JSON `/api/v1`) — ce routeur Jinja2 ne fait que déléguer
et rendre le template `_atelier.html`. Il est conservé jusqu'à la bascule F5
(retrait de Jinja2/HTMX/Alpine), l'écran E5 étant déjà servi par le SPA Svelte.

Modèle d'interaction (décisions de l'auteur, J2.5 + R2) :
- le « texte affiché » est la PROJECTION calculée depuis la base immuable +
  annotations ; « Valider la version actuelle » enregistre EXACTEMENT le texte
  affiché, qu'il soit corrigé ou non ;
- l'Embellissement et les alternatives se demandent par SÉLECTION + clic droit ;
- la validation officielle n'existe que pour les Chapitres ;
- toute écriture dans `chapitres` est précédée d'un backup natif SQLite.
"""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.routes.web import TEMPLATES, _analyse
from app.services import atelier as service_atelier
from app.services.atelier import (
    ErreurAtelier,
    appliquer_alternative,
    appliquer_embellissement,
    charger_etat,
    choisir_forme,
    editer_paragraphe,
    nouvelle_version,
    reevaluer,
    suggerer_alternatives,
    suggerer_embellissement,
    valider,
)

router = APIRouter()


async def _verifier_analyse_terminee(identifiant: int):
    """Retourne `(analyse, None)` si l'analyse existe et est terminée, sinon
    `(None, réponse HTTP d'erreur)`."""
    analyse = await _analyse(identifiant)
    if not analyse or analyse["statut"] != "terminee":
        return None, HTMLResponse("Analyse introuvable ou non terminée.", status_code=404)
    return analyse, None


def _rendre_atelier(request: Request, analyse, etat, erreur=None, onglet="tout"):
    """Rend le document annoté (projection de l'onglet) via le service partagé."""
    return TEMPLATES.TemplateResponse(
        request,
        "analyses/_atelier.html",
        service_atelier.contexte_resultat(analyse, etat, erreur, onglet),
    )


@router.get("/analyses/{identifiant}")
async def page_analyse(request: Request, identifiant: int):
    analyse = await _analyse(identifiant)
    if analyse is None:
        return HTMLResponse("Analyse introuvable.", status_code=404)
    statut = analyse["statut"]
    if statut in ("en_attente", "en_cours"):
        return TEMPLATES.TemplateResponse(request, "analyses/suivi.html", {"analyse": analyse})
    if statut in ("echec", "rejetee"):
        return TEMPLATES.TemplateResponse(request, "analyses/erreur.html", {"analyse": analyse})

    etat = await charger_etat(analyse)
    return TEMPLATES.TemplateResponse(
        request, "analyses/resultat.html",
        service_atelier.contexte_resultat(
            analyse, etat, onglet=request.query_params.get("onglet", "tout")
        ),
    )


@router.post("/analyses/{identifiant}/onglet")
async def changer_onglet(
    request: Request,
    identifiant: int,
    onglet: str = Form("tout"),
):
    """Change d'onglet (projection par phase, jalon R1-a) : AUCUN état modifié,
    le document est simplement re-rendu avec la projection de l'onglet demandé."""
    analyse, reponse_erreur = await _verifier_analyse_terminee(identifiant)
    if reponse_erreur is not None:
        return reponse_erreur
    etat = await charger_etat(analyse)
    return _rendre_atelier(request, analyse, etat, onglet=onglet)


@router.post("/analyses/{identifiant}/choix-forme")
async def choix_forme(
    request: Request,
    identifiant: int,
    correction_id: str = Form(...),
    decision: str = Form(...),
    onglet: str = Form("tout"),
):
    """Accepte ('corrige', défaut) ou refuse ('original') une correction Forme :
    un simple FILTRE (jalon R2) — aucun remappage, la projection se recalcule."""
    analyse, reponse_erreur = await _verifier_analyse_terminee(identifiant)
    if reponse_erreur is not None:
        return reponse_erreur
    etat = await charger_etat(analyse)
    try:
        await choisir_forme(analyse, etat, correction_id, decision)
    except ErreurAtelier as erreur:
        return HTMLResponse(str(erreur), status_code=erreur.statut)
    return _rendre_atelier(request, analyse, etat, onglet=onglet)


@router.post("/analyses/{identifiant}/appliquer-alternative")
async def route_appliquer_alternative(
    request: Request,
    identifiant: int,
    paragraphe_id: str = Form(...),
    fragment: str = Form(...),
    texte: str = Form(...),
    contexte: str = Form(""),
    onglet: str = Form("tout"),
):
    """Applique l'alternative choisie par l'auteur (clic droit sur sélection)."""
    analyse, reponse_erreur = await _verifier_analyse_terminee(identifiant)
    if reponse_erreur is not None:
        return reponse_erreur
    etat = await charger_etat(analyse)
    try:
        await appliquer_alternative(analyse, etat, paragraphe_id, fragment, texte, contexte)
    except ErreurAtelier as erreur:
        return _rendre_atelier(request, analyse, etat, str(erreur), onglet=onglet)
    return _rendre_atelier(request, analyse, etat, onglet=onglet)


@router.post("/analyses/{identifiant}/editer")
async def route_editer_paragraphe(
    request: Request,
    identifiant: int,
    paragraphe_id: str = Form(...),
    texte: str = Form(...),
    onglet: str = Form("tout"),
):
    """Édition DIRECTE sans IA temps réel (UX4, décision 38) : le texte du
    paragraphe affiché est remplacé par la saisie de l'auteur (un patch ancré
    base) ; « ↻ Re-corriger » soumet une nouvelle version ensuite."""
    analyse, reponse_erreur = await _verifier_analyse_terminee(identifiant)
    if reponse_erreur is not None:
        return reponse_erreur
    etat = await charger_etat(analyse)
    try:
        await editer_paragraphe(analyse, etat, paragraphe_id, texte)
    except ErreurAtelier as erreur:
        return _rendre_atelier(request, analyse, etat, str(erreur), onglet=onglet)
    return _rendre_atelier(request, analyse, etat, onglet=onglet)


@router.post("/analyses/{identifiant}/reevaluer")
async def route_reevaluer(
    request: Request,
    identifiant: int,
    paragraphe_id: str = Form(...),
    onglet: str = Form("tout"),
):
    """Réévaluation manuelle des corrections d'un paragraphe (bouton « ↻ »)."""
    analyse, reponse_erreur = await _verifier_analyse_terminee(identifiant)
    if reponse_erreur is not None:
        return reponse_erreur
    etat = await charger_etat(analyse)
    try:
        await reevaluer(analyse, etat, paragraphe_id)
    except ErreurAtelier as erreur:
        return _rendre_atelier(request, analyse, etat, str(erreur), onglet=onglet)
    return _rendre_atelier(request, analyse, etat, onglet=onglet)


@router.post("/analyses/{identifiant}/appliquer-embellissement")
async def route_appliquer_embellissement(
    request: Request,
    identifiant: int,
    paragraphe_id: str = Form(...),
    fragment: str = Form(...),
    texte: str = Form(...),
    contexte: str = Form(""),
    onglet: str = Form("tout"),
):
    """Applique l'embellissement choisi, PUIS réévalue les corrections du
    paragraphe. Zéro surprise : si la réévaluation échoue, RIEN n'est appliqué
    (aucun état partiel)."""
    analyse, reponse_erreur = await _verifier_analyse_terminee(identifiant)
    if reponse_erreur is not None:
        return reponse_erreur
    etat = await charger_etat(analyse)
    try:
        await appliquer_embellissement(
            analyse, etat, paragraphe_id, fragment, texte, contexte
        )
    except ErreurAtelier as erreur:
        return _rendre_atelier(request, analyse, etat, str(erreur), onglet=onglet)
    return _rendre_atelier(request, analyse, etat, onglet=onglet)


# --- Suggestions à la demande (JSON, aucun état modifié) ----------------------


@router.post("/api/embellir")
async def api_embellir(demande: dict):
    """Propose une réécriture embellie du passage sélectionné (contexte pris en
    compte). Aucun état modifié : l'auteur voit puis applique ou annule."""
    return await suggerer_embellissement(
        demande.get("fragment", ""),
        demande.get("paragraphe_texte", ""),
        demande.get("contexte", ""),
    )


@router.post("/api/alternatives")
async def api_alternatives(demande: dict):
    """Propose des alternatives (synonymes, champ lexical) cohérentes avec le
    contexte du passage sélectionné (clic droit). Aucun état modifié."""
    return await suggerer_alternatives(
        demande.get("fragment", ""), demande.get("paragraphe_texte", "")
    )


# --- Workflow de fin de chapitre (J2.5) ---------------------------------------


@router.post("/analyses/{identifiant}/nouvelle-version")
async def relancer_nouvelle_version(identifiant: int):
    """Soumet une NOUVELLE analyse dont le texte source est exactement le texte
    courant (le texte affiché, avec les choix et modifications de l'auteur)."""
    analyse, reponse_erreur = await _verifier_analyse_terminee(identifiant)
    if reponse_erreur is not None:
        return reponse_erreur
    try:
        nouvel_id = await nouvelle_version(analyse)
    except Exception as erreur:  # noqa: BLE001 — message explicite, jamais de fantôme
        return HTMLResponse(
            f"Erreur lors de la création de la nouvelle version : {erreur}",
            status_code=500,
        )
    # ATTENTION (piège J2.1) : la redirection doit pointer vers le NOUVEL id.
    return RedirectResponse(f"/analyses/{nouvel_id}", status_code=303)


@router.post("/analyses/{identifiant}/valider")
async def valider_version_officielle(identifiant: int):
    """Valide officiellement le chapitre : enregistre dans `chapitres` le TEXTE
    AFFICHÉ au moment du clic (qu'il soit corrigé ou non), avec son hash
    SHA-256, après un backup natif SQLite ; « dernier validé gagne » fait
    avancer la chaîne N+1. Réservé aux Chapitres (Passage/Extrait : 400)."""
    analyse = await _analyse(identifiant)
    if analyse is None:
        return HTMLResponse("Analyse introuvable.", status_code=404)
    try:
        await valider(analyse)
    except ErreurAtelier as erreur:
        return HTMLResponse(str(erreur), status_code=erreur.statut)
    return RedirectResponse(f"/analyses/{identifiant}", status_code=303)