"""Écrans web — E1 Accueil/Projets + E3 Soumission + E4 Suivi (cahier des
charges §6). L'écran E5 (atelier de relecture, alternatives/embellissement à
la demande, validation, workflow de fin de chapitre) vit dans
`app/routes/atelier.py` (jalon J2.5)."""

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
from app.services import analyse as service_analyse

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


async def _projet_actif():
    actif = await _projet_actif_id()
    if not actif:
        return None
    lignes = await db.interroger("SELECT * FROM projets WHERE projet_id = ?", (actif,))
    return lignes[0] if lignes else None


async def _analyse(identifiant: int):
    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (identifiant,))
    return lignes[0] if lignes else None


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


async def _dernieres_options() -> dict:
    """Mémoire des dernières configurations (J2.5) : catégorie + phases
    re-proposées pré-cochées quand l'auteur revient soumettre un autre texte."""
    lignes = await db.interroger(
        "SELECT valeur FROM parametres WHERE cle = 'dernieres_options'"
    )
    return json.loads(lignes[0]["valeur"]) if lignes else {}


def _normaliser_prefil(brut: dict) -> dict:
    categorie = (
        brut.get("categorie")
        if brut.get("categorie") in ("chapitre", "passage", "extrait")
        else "chapitre"
    )
    phases = brut.get("phases") or {}
    defaut = {"forme": True, "style": True, "technique": categorie == "chapitre"}
    return {
        "categorie": categorie,
        **{k: bool(phases.get(k, defaut[k])) for k in ("forme", "style", "technique")},
    }


def _contexte_nouveau(projet, erreur=None, prefil=None):
    from app.services.chaine import numero_attendu
    attendu = numero_attendu(projet) if projet else 0.0
    return {
        "projet": projet,
        "max_caracteres": settings.max_caracteres,
        "numero_attendu": int(attendu) if attendu == int(attendu) else attendu,
        "erreur": erreur,
        "prefil": _normaliser_prefil(prefil or {}),
    }


def _choix_phases(brut: str) -> dict[str, bool | None]:
    """Décode le champ caché `phases` du formulaire (JSON écrit par le JS).
    Retourne {} si absent/vide → pré-sélection. J2.5 : trois phases seulement
    (Forme, Style, Technique) — l'Embellissement est demandé à la demande."""
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
        for phase in ("forme", "style", "technique")
        if phase in donnees
    }


@router.get("/analyses/nouveau")
async def formulaire_analyse(request: Request):
    return TEMPLATES.TemplateResponse(
        request,
        "analyses/nouveau.html",
        _contexte_nouveau(await _projet_actif(), prefil=await _dernieres_options()),
    )


@router.post("/analyses")
async def soumettre_analyse(
    request: Request,
    texte: str = Form(...),
    categorie: str = Form("chapitre"),
    numero_chapitre: str = Form(""),
    avec_codex: str = Form(""),
    phases: str = Form(""),
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
            erreur = "Sélectionnez au moins un type de correction (Forme, Style ou Technique)."
    if erreur:
        return TEMPLATES.TemplateResponse(
            request, "analyses/nouveau.html", _contexte_nouveau(projet, erreur),
            status_code=400,
        )

    cat_choisie = categorie if categorie in ("chapitre", "passage", "extrait") else "chapitre"

    num_chap = None
    if cat_choisie == "chapitre" and numero_chapitre.strip():
        try:
            num_chap = float(numero_chapitre.strip())
        except ValueError:
            num_chap = None

    options = {
        "categorie": cat_choisie,
        "numero_chapitre": num_chap,
        "avec_codex": avec_codex == "on" if cat_choisie == "chapitre" else False,
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
        (projet["projet_id"], texte, json.dumps(options, ensure_ascii=False)),
    )
    tache = asyncio.create_task(service_analyse.executer(identifiant))
    _TACHES.add(tache)
    tache.add_done_callback(_TACHES.discard)
    return RedirectResponse(f"/analyses/{identifiant}", status_code=303)


# --- E4 : fragment HTMX de polling (cahier des charges §4.4) -------------------


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