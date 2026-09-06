"""Fixtures communes — base isolée par test (dossier temporaire)."""

import pytest

from app.config import settings


@pytest.fixture()
def dossier_donnees(tmp_path, monkeypatch):
    """Redirige data_dir vers un dossier temporaire : chaque test a sa base vierge."""
    dossier = tmp_path / "data"
    monkeypatch.setattr(settings, "data_dir", dossier)
    return dossier


@pytest.fixture()
def base_donnees(dossier_donnees):
    """Initialise la base idempotemment et retourne le chemin du fichier SQLite."""
    from app import db

    db.init_db()
    return dossier_donnees / "database.sqlite3"


@pytest.fixture()
def connexion(base_donnees):
    """Connexion SQLite directe (tests de schéma), avec clés étrangères actives."""
    import sqlite3

    conn = sqlite3.connect(base_donnees)
    conn.execute("PRAGMA foreign_keys=ON")
    yield conn
    conn.close()


@pytest.fixture()
def client(dossier_donnees):
    """Client de test FastAPI — le cycle de vie (lifespan) initialise la base."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
