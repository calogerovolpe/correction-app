"""Accès SQLite — v6 §3 et §15 : WAL, busy_timeout, integrity_check à l'initialisation,
opérations via asyncio.to_thread (sqlite3 est synchrone), verrou applicatif (mono-utilisateur)."""

import asyncio
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

from app.config import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Verrou de sérialisation des accès SQLite (cahier des charges A6 / v6 §15).
# threading.Lock — agnostique de la boucle d'événements (un asyncio.Lock se lie
# à sa première boucle, ce qui brise les boucles multiples des tests), suffisant
# pour un usage mono-utilisateur ; WAL + busy_timeout en filet de sécurité.
_VERROU = threading.Lock()


def _connecter() -> sqlite3.Connection:
    """Ouvre une connexion avec les pragmas requis (v6 §3)."""
    conn = sqlite3.connect(settings.data_dir / "database.sqlite3")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialisation idempotente (v6 §3) : arborescence, tables, integrity_check."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "backups").mkdir(exist_ok=True)
    (settings.data_dir / "logs").mkdir(exist_ok=True)

    conn = _connecter()
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
        etat = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if etat != "ok":
            raise RuntimeError(f"integrity_check a échoué : {etat}")
    finally:
        conn.close()


def _executer_sync(sql: str, params: Iterable[Any], many: bool) -> tuple[int, int]:
    with _VERROU:
        conn = _connecter()
        try:
            cur = conn.executemany(sql, params) if many else conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid, cur.rowcount
        finally:
            conn.close()


def _interroger_sync(sql: str, params: Iterable[Any]) -> list[dict]:
    with _VERROU:
        conn = _connecter()
        try:
            lignes = conn.execute(sql, params).fetchall()
            return [dict(ligne) for ligne in lignes]
        finally:
            conn.close()


async def executer(sql: str, params: Iterable[Any] = ()) -> tuple[int, int]:
    """Exécute une écriture (INSERT/UPDATE/DELETE/DDL). Retourne (lastrowid, rowcount)."""
    return await asyncio.to_thread(_executer_sync, sql, params, False)


async def interroger(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    """Exécute une lecture et retourne les lignes en dictionnaires."""
    return await asyncio.to_thread(_interroger_sync, sql, params)
