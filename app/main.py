"""Application FastAPI — point d'entrée (cahier des charges §4.1)."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.routes import web

DOSSIER_APP = Path(__file__).parent


@asynccontextmanager
async def cycle_de_vie(_: FastAPI):
    """Initialisation idempotente à chaque démarrage (v6 §3)."""
    db.init_db()
    yield


app = FastAPI(title="Correction de manuscrit", lifespan=cycle_de_vie)
app.mount("/static", StaticFiles(directory=DOSSIER_APP / "static"), name="static")
app.include_router(web.router)
