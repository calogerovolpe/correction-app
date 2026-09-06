# correction-app — Application web de correction de manuscrit

Implémentation de l'application décrite par **`docs/Architecture application web — v1 (spécification consolidée).md`** — LA source de vérité du projet (métier + applicatif), versionnée avec le code.
Historique de conception : `docs/Cahier des charges — Application web de correction de manuscrit.md` (remplacé par la spec consolidée).

**Jalon courant : J2 — MVP de relecture** : écran E3 (soumission, catégorisation auto, matrice de phases, forçage Passage/Extrait, remplacement officiel, garde-fou taille), jobs asynchrones suivis par HTMX (E4), phases 3-6 parallèles via l'API Mistral (fail-fast, Option B), document annoté E5 (couleurs WCAG AA, tooltips, pastilles filtres, bouton « Lecture Embellissement », navigation clavier, compteur de paragraphes masqués). **Validé de bout en bout avec Mistral Small sur un vrai chapitre.** Jalons J0 (socle) et J1 (moteur métier) validés.

## Lancement local

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

→ http://localhost:8000 (la base `data/database.sqlite3` et les dossiers `backups/`/`logs/` sont créés automatiquement).

## Configuration LLM (Mistral — clé API uniquement)

L'application fonctionne **uniquement par clé API Mistral** (décision de l'auteur — aucun LLM local) :

1. Copiez `.env.example` vers `.env` ;
2. Renseignez `APP_LLM_API_KEY` avec votre clé Mistral ;
3. Les cinq phases utilisent `mistral-small-latest` par défaut.

Vérification de la connexion (ping fail-fast, `max_tokens=5`, coût négligeable) :

```powershell
python scripts/tester_llm.py
```

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

Voir la spec consolidée §2.2 (`docs/`). Résumé : `app/` (FastAPI, services, routes, templates), `tests/` (pytest), `data/` (SQLite + backups + logs, ignoré par git), `exports/`, `docs/` (spécification versionnée).
