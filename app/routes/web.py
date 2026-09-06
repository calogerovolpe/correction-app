"""Écrans web — E1 Accueil / Projets (cahier des charges §6, version J0 minimale)."""

import secrets
import string
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
router = APIRouter()


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
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {"projets": projets, "actif_id": await _projet_actif_id()},
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
