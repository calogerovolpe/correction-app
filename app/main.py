"""Application FastAPI — point d'entrée (cahier des charges §4.1)."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.routes import atelier, web

DOSSIER_APP = Path(__file__).parent


@asynccontextmanager
async def cycle_de_vie(_: FastAPI):
    """Initialisation idempotente à chaque démarrage (v6 §3) + récupération des
    jobs orphelins : une analyse interrompue par un redémarrage passe en `echec`
    explicite — jamais de statut fantôme (cahier des charges §4.4)."""
    db.init_db()
    await db.executer(
        "UPDATE analyses SET statut = 'echec', "
        "erreur = 'Interrompue par un redémarrage du serveur — resoumettez le texte.', "
        "fini_a = datetime('now') "
        "WHERE statut IN ('en_attente', 'en_cours')",
        (),
    )
    yield


app = FastAPI(title="Correction de manuscrit", lifespan=cycle_de_vie)
app.mount("/static", StaticFiles(directory=DOSSIER_APP / "static"), name="static")
app.include_router(web.router)
app.include_router(atelier.router)
