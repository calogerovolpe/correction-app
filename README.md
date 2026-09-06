# correction-app — Application web de correction de manuscrit

Implémentation du **cahier des charges** `../Cahier des charges — Application web de correction de manuscrit.md`.
Le métier (normalisation, chaîne $N+1$, codex, déduplication, alertes) est défini par la **spécification v6** du dossier parent — elle fait foi.

**Jalon courant : J1 — Moteur métier** : normalisation (§8.1), réconciliation des offsets et déduplication Style prioritaire (§8.3-8.5), machine d'états $N+1$ et remplacement officiel (§6.5-6.6), alertes à numérotation stable avec double barrière `/nopb` (§6.7), couche LLM compatible OpenAI (fail-fast, timeouts) et mock LLM déterministe pour les tests. Le jalon J0 (socle FastAPI, schéma SQLite, écran E1, Docker) est validé.

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
