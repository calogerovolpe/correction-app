# correction-app — Application web de correction de manuscrit

> **Pointeur** : la source de vérité de l'**état du projet** (jalons, contexte actif,
> décisions, méthode de travail) est la **Memory Bank** (`memory-bank/`) — lire
> d'abord `memory-bank/activeContext.md`. La source de vérité de la
> **spécification** est `docs/Architecture application web — v1 (spécification
> consolidée).md` (versionnée avec le code).

## Lancement local

Double-cliquez `Ouvrir Correction.bat` (démarre le serveur et ouvre le navigateur),
ou manuellement :

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

→ http://localhost:8000 (la base `data/database.sqlite3` et les dossiers `backups/`/`logs/` sont créés automatiquement).

## Configuration LLM (Mistral — clé API uniquement)

1. Copiez `.env.example` vers `.env` ;
2. Renseignez `APP_LLM_API_KEY` avec votre clé Mistral ;
3. Les phases utilisent `mistral-small-latest` par défaut.

Vérification de la connexion (ping fail-fast, coût négligeable) :

```powershell
python scripts/tester_llm.py
```

## Tests

```powershell
pytest
```

E2E réel Mistral (environnement de données isolé `data_e2e/`, jamais votre manuscrit) :

```powershell
python scripts/e2e_j25.py
```

## Docker (parité dev/prod)

```powershell
Copy-Item .env.example .env
docker compose up --build
```
