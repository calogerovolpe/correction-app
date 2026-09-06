# correction-app — Application web de correction de manuscrit

Implémentation du **cahier des charges** `../Cahier des charges — Application web de correction de manuscrit.md`.
Le métier (normalisation, chaîne $N+1$, codex, déduplication, alertes) est défini par la **spécification v6** du dossier parent — elle fait foi.

**Jalon courant : J0 — Socle** : squelette FastAPI, schéma SQLite complet (v6 §6.2, renommé projets), page d'accueil E1 minimale, Docker, tests de schéma.

## Lancement local

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

→ http://localhost:8000 (la base `data/database.sqlite3` et les dossiers `backups/`/`logs/` sont créés automatiquement).

## Tests

```powershell
pytest
```

## Docker (parité dev/prod)

```powershell
Copy-Item .env.example .env
docker compose up --build
```

## Structure

Voir le cahier des charges §4.2. Résumé : `app/` (FastAPI, services, routes, templates), `tests/` (pytest), `data/` (SQLite + backups + logs, ignoré par git), `exports/`.
