# Contexte technique — stack, setup, commandes, contraintes

> Dernière mise à jour : 2026-09-07.

## Stack

> **Refonte frontend EN COURS — F3 livré** (`023534a`) : Svelte 5 + TypeScript +
> Vite → `app/static/spa/` (gitignoré), API JSON `/api/v1/` (`app/routes/api.py` :
> projets E1, analyses récentes, soumission E3 + suivi E4, **atelier E5**
> `GET /api/v1/analyses/{id}/atelier` + actions — réutilise les services purs
> existants ET l'orchestrateur `app/services/atelier.py` partagé), routes Jinja2
> conservées jusqu'à F5. Source de vérité : `plan-refonte-frontend.md`.
> ⚠️ **Les écrans E1 (accueil), E3 (soumission), E4 (suivi) et E5 (atelier) sont
> servis par le SPA compilé** (repli Jinja2 si le build est absent ; E5 est
> encore rendu par les routes Jinja2, déléguant à `app/services/atelier.py`,
> jusqu'à la bascule F5).
| Couche | Choix |
|---|---|
| Backend | Python 3.11+ (3.14.3 en pratique), FastAPI, Uvicorn, Pydantic v2, pydantic-settings (préfixe `APP_`, lit `.env`), httpx, python-multipart |
| Frontend | Jinja2 (autoescape) + HTMX (polling) + Alpine.js — servis depuis `app/static/vendor/`, aucun CDN, aucun build Node |
| Frontend (refonte F0→F5) | **Svelte 5 + TypeScript + Vite** — `frontend/` versionné (F0 ✅ `4cbb55c`, F1 ✅ `cb6abc1`, F2 ✅ `6cdfb22`, F3 ✅ `023534a`), build → `app/static/spa/` (gitignoré) ; **accueil E1 depuis F1, soumission E3 + suivi E4 depuis F2, atelier E5 depuis F3** ; tests Vitest (`npm test` — **45**) |
| Base de données | SQLite WAL, `busy_timeout=15000`, accès `asyncio.to_thread`, verrou `threading.Lock` (`app/db.py`) |
| LLM | **Mistral API uniquement**, `mistral-small-latest` ; client maison compatible OpenAI (`app/llm/client.py`) |
| Conteneurisation | Dockerfile + docker-compose.yml (parité dev/prod) |
| Tests | pytest — **176 tests** (dont **32 tests d'intégration TestClient/MockLLM sur `/api/v1/`** : 17 F2 + 15 atelier/projets F3/FA1/FA2/FA3) + **48 Vitest** (frontend Svelte) + E2E réel Mistral (`scripts/e2e_j25.py`, isolé `data_e2e/`) |

## Setup de développement

- venv : `.venv\` (déjà créé, Python 3.14.3). Racine du projet : `Application web\correction-app\`.
- `.env` (jamais commité) : `APP_LLM_API_KEY` (clé Mistral), `APP_LLM_BASE_URL`, modèles par phase, garde-fous (`APP_MAX_CARACTERES=30000`, timeouts, températures, variante). Modèle public : `.env.example`.
- `data/database.sqlite3`, `backups/`, `logs/` créés automatiquement au démarrage (gitignorés).

## Commandes (PowerShell, depuis la racine du projet)

```powershell
.venv\Scripts\python -m pytest -q            # tests — OBLIGATOIRE avant tout commit (121 verts attendus)
.venv\Scripts\python -m uvicorn app.main:app --reload   # serveur dev → http://localhost:8000
.venv\Scripts\python scripts\tester_llm.py   # ping fail-fast des modèles Mistral (coût négligeable)
.venv\Scripts\python scripts\e2e_j25.py      # E2E réel Mistral — environnement de données ISOLÉ (data_e2e/)
docker compose up --build                    # Docker (copier .env.example → .env si absent)
```

## Boucle de validation d'un jalon (MÉTHODE OBLIGATOIRE)

1. **Mode Plan d'abord** : plan présenté à l'auteur, attendre son feu vert.
2. Coder par petites étapes.
3. **`pytest` 100 % verts** avant toute autre chose.
4. **Test E2E réel** si le pipeline LLM est touché (uvicorn port 8124, soumission via `curl.exe`, vérifier le HTML de résultat, arrêter le serveur).
5. **Mettre à jour la Memory Bank** (`activeContext.md` + `progress.md`).
6. `git add -A` + commit (`Jn — <contenu> — N tests verts`) + `git push`.

## Règles de tests

- Toute correction de bug = **un test de régression**.
- Fixtures (`tests/conftest.py`) : `dossier_donnees` (base isolée en tmp), `base_donnees`, `connexion` (SQL direct), `client` (TestClient).
- Attendre la fin d'un job : polling HTTP via `_attendre()`, jamais d'accès DB direct concurrent pendant qu'un job tourne.
- Aucun test pytest n'appelle la vraie API Mistral (mock) ; E2E réel = exception manuelle, hors pytest.

## Contraintes

- **Local-first** : aucune télémétrie, aucun CDN ni police distante, HTMX/Alpine locaux.
- **Mistral uniquement** (décision A4) ; clé jamais commitée, jamais lue hors `config.py` / `scripts/tester_llm.py`.
- **Manuscrit** (`data/`) : ne quitte jamais la machine — ne jamais committer/exporter de texte soumis.

## Fichiers protégés / interdits

| Fichier | Règle |
|---|---|
| `.env` | Clé API réelle — ne jamais afficher, committer, copier dans un test |
| `.env.example` | Modèle public (clé factice uniquement) |
| `app/static/vendor/` | Librairies locales — ne pas éditer, pas de CDN |
| `data/` | Manuscrit + base + backups + logs — ne jamais supprimer ni committer |
| `app/schema.sql` | Schéma de référence — évolutions idempotentes justifiées par la spec |
| `tests/` existants | Ne jamais supprimer/affaiblir un test pour le faire passer |
| Palette WCAG AA | Ne pas changer sans arbitrage de l'auteur |

**Ne jamais** : committer `.env`/`data/`/`exports/` ; introduire un CDN ; appeler Mistral depuis pytest ; modifier Option B / fail-fast / liste-vide-jamais-panne.

## Git

- Remote : `https://github.com/calogerovolpe/correction-app` (privé), branche `master`.
- Identité : `calogerovolpe <bx.volpe@gmail.com>`.
- Un commit par jalon ou correctif, push systématique.

## Documents de référence

- **Spécification détaillée** (métier + applicatif) : `docs/Architecture application web — v1 (spécification consolidée).md` — source de vérité de la *spécification*, committée avec le code.
- Historique de conception : `docs/Cahier des charges — ….md` (remplacé, archive).
- Archives de la genèse (fonction OpenWebUI) : dossier grand-parent **hors repo**, `Architecture fonction correction de texte — v3/v4/v5/v6.md` — ne pas coder avec, ne pas copier dans le repo.