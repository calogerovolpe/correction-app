"""Écrans web — E1 Accueil/Projets + E3 Soumission + E4 Suivi + E5 Résultat (cahier des charges §6)."""

import asyncio
import json
import secrets
import string
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db
from app.config import settings
from app.models import CorrectionFusionnee
from app.services import analyse as service_analyse
from app.services import rendu as service_rendu
from app.services.normalisation import decouper_paragraphes, normaliser

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
router = APIRouter()

# Références fortes des tâches asynchrones (jobs d'analyse — cahier §4.4)
_TACHES: set[asyncio.Task] = set()


def _nouvel_id() -> str:
    """Format P-XXXXXX, 6 caractères aléatoires base36 (v6 §6.3, adapté projets)."""
    alphabet = string.digits + string.ascii_uppercase
    return "P-" + "".join(secrets.choice(alphabet) for _ in range(6))


async def _projet_actif_id() -> str | None:
    lignes = await db.interroger("SELECT valeur FROM parametres WHERE cle = 'projet_actif'")
    return lignes[0]["valeur"] if lignes else None


@router.get("/")
async def accueil(request: Request):
    projets = await db.interroger("SELECT * FROM projets ORDER BY created_at DESC, projet_id DESC")
    analyses = await db.interroger(
        "SELECT id, statut, categorie, substr(texte_source, 1, 60) AS extrait, cree_a "
        "FROM analyses ORDER BY id DESC LIMIT 10"
    )
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {"projets": projets, "actif_id": await _projet_actif_id(), "analyses": analyses},
    )


@router.post("/projets")
async def creer_projet(titre: str = Form(...)):
    titre = titre.strip()
    if not titre:
        return RedirectResponse("/", status_code=303)
    projet_id = _nouvel_id()
    await db.executer(
        "INSERT INTO projets (projet_id, titre) VALUES (?, ?)", (projet_id, titre)
    )
    # Premier projet d'un espace vierge : devient automatiquement actif (v6 §6.3)
    if await _projet_actif_id() is None:
        await db.executer(
            "INSERT INTO parametres (cle, valeur) VALUES ('projet_actif', ?)", (projet_id,)
        )
    return RedirectResponse("/", status_code=303)


# --- E3 : soumission d'un texte (cahier des charges §6-E3) --------------------


async def _projet_actif():
    actif = await _projet_actif_id()
    if not actif:
        return None
    lignes = await db.interroger("SELECT * FROM projets WHERE projet_id = ?", (actif,))
    return lignes[0] if lignes else None


async def _analyse(identifiant: int):
    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (identifiant,))
    return lignes[0] if lignes else None


def _contexte_nouveau(projet, erreur=None):
    return {
        "projet": projet,
        "max_caracteres": settings.max_caracteres,
        "temperature_defaut": settings.temperature_embellissement,
        "erreur": erreur,
    }


def _choix_phases(brut: str) -> dict[str, bool | None]:
    """Décode le champ caché `phases` du formulaire (JSON {"forme": true, ...} écrit par le JS).

    Retourne {} si absent/vide → pré-sélection matrice (v6 §5.4).
    Décision de l'auteur (J2) : la matrice n'est plus rigide — elle pré-coche,
    l'utilisateur décoche/coche librement chaque phase."""
    if not brut:
        return {}
    try:
        donnees = json.loads(brut)
    except ValueError:
        return {}
    if not isinstance(donnees, dict):
        return {}
    return {
        phase: bool(donnees[phase])
        for phase in ("forme", "style", "technique", "embellissement")
        if phase in donnees
    }


@router.get("/analyses/nouveau")
async def formulaire_analyse(request: Request):
    return TEMPLATES.TemplateResponse(
        request, "analyses/nouveau.html", _contexte_nouveau(await _projet_actif())
    )


@router.post("/analyses")
async def soumettre_analyse(
    request: Request,
    texte: str = Form(...),
    categorie: str = Form("auto"),
    phases: str = Form(""),
    temperature_embellissement: str = Form(""),
    remplacement: str = Form(""),
):
    projet = await _projet_actif()
    erreur = None
    if projet is None:
        erreur = "Aucun projet actif : créez d'abord un projet (roman) sur la page d'accueil."
    elif not texte.strip():
        erreur = "Le texte soumis est vide."
    elif len(texte) > settings.max_caracteres:
        erreur = (
            f"Texte de {len(texte)} caractères — la limite est de {settings.max_caracteres}. "
            "Refus explicite : aucune troncature silencieuse du contexte (v6 §2.3)."
        )
    else:
        choix = _choix_phases(phases)
        if choix and not any(choix.values()):
            erreur = "Sélectionnez au moins un type de correction (Forme, Style, Technique ou Embellissement)."
    if erreur:
        return TEMPLATES.TemplateResponse(
            request, "analyses/nouveau.html", _contexte_nouveau(projet, erreur),
            status_code=400,
        )

    try:
        temperature = float(temperature_embellissement) if temperature_embellissement else None
    except ValueError:
        temperature = None

    options = {
        "categorie": categorie if categorie in ("auto", "passage", "extrait") else "auto",
        "forme": choix.get("forme"),
        "style": choix.get("style"),
        "technique": choix.get("technique"),
        "embellissement": choix.get("embellissement"),
        "remplacement": remplacement == "on",
        "temperature_embellissement": temperature,
    }
    identifiant, _ = await db.executer(
        "INSERT INTO analyses (projet_id, texte_source, options_json) VALUES (?, ?, ?)",
        (projet["projet_id"], texte, json.dumps(options, ensure_ascii=False)),
    )
    tache = asyncio.create_task(service_analyse.executer(identifiant))
    _TACHES.add(tache)
    tache.add_done_callback(_TACHES.discard)
    return RedirectResponse(f"/analyses/{identifiant}", status_code=303)


# --- E4 : suivi du job / E5 : résultat (cahier des charges §6-E4, E5) ----------


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

    # terminee -> E5 : document annoté (v6 §7)
    lignes = await db.interroger(
        "SELECT data_json FROM corrections WHERE analyse_id = ? ORDER BY id", (identifiant,)
    )
    fusion = []
    if lignes:
        fusion = [CorrectionFusionnee.model_validate(d) for d in json.loads(lignes[0]["data_json"])]
    paragraphes = decouper_paragraphes(normaliser(analyse["texte_source"]))
    document = service_rendu.preparer_document(fusion, paragraphes)
    avec_embellissements = any(
        f.correction.phase == "embellissement" or f.embellissement_migre is not None
        for f in fusion
    )
    return TEMPLATES.TemplateResponse(
        request,
        "analyses/resultat.html",
        {
            "analyse": analyse,
            "document": document,
            "avec_embellissements": avec_embellissements,
            "nb_corrections": len(fusion),
        },
    )


@router.get("/analyses/{identifiant}/fragment")
async def fragment_analyse(request: Request, identifiant: int):
    """Fragment HTMX de polling (cahier §4.4) : statut en cours, redirection si final."""
    analyse = await _analyse(identifiant)
    if analyse is None:
        return HTMLResponse("", status_code=404)
    if analyse["statut"] in ("terminee", "echec", "rejetee"):
        reponse = HTMLResponse("")
        reponse.headers["HX-Redirect"] = f"/analyses/{identifiant}"
        return reponse
    return TEMPLATES.TemplateResponse(request, "analyses/fragment_statut.html",
                                     {"analyse": analyse})
