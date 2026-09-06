# Contexte projet — LIRE EN PREMIER

## Qu'est-ce que ce projet ?
Application web **privée, mono-utilisateur** de correction de manuscrit littéraire
(Chapitre / Passage / Extrait). L'auteur soumet un texte, 4 phases LLM parallèles le
corrigent (Forme, Style, Technique, Embellissement), le résultat s'affiche en document
annoté interactif. Un codex narratif persistant (personnages, glossaire…) mémorise le
roman au fil des chapitres officiels (chaîne N+1 stricte).

## Documents de référence — source de vérité (PAS dans le repo, dans le dossier parent)
1. **Spécification métier v6** : `..\..\Architecture fonction correction de texte — v6 (spécification complète).md`
   → Toute règle métier (chaîne, déduplication, offsets, alertes, rendu) y est définie
   section par section. **En cas de doute métier : la v6 fait foi.**
2. **Cahier des charges applicatif** : `..\..\Cahier des charges — Application web de correction de manuscrit.md`
   → Stack, écrans E1-E9, jalons J0-J5, exigences. **En cas de doute applicatif : il fait foi.**

## Stack (décisions A1-A9 du cahier des charges — ne pas changer sans arbitrage de l'auteur)
- **Backend** : Python 3.11+ (3.14 en pratique), FastAPI, Uvicorn, Pydantic v2
- **Frontend** : Jinja2 + HTMX + Alpine.js — **servis localement** (`app/static/vendor/`),
  aucun CDN, pas de build Node
- **Base** : SQLite WAL, `busy_timeout=15000`, accès via `asyncio.to_thread`, verrou
  `threading.Lock` (PAS un `asyncio.Lock` — voir conventions)
- **LLM** : **Mistral API uniquement** (`mistral-small-latest` pour les 5 phases),
  client maison compatible OpenAI (`app/llm/client.py`), clé dans `.env` (jamais commitée)

## Répartition du code
```
app/
├── main.py          # FastAPI, lifespan (init_db + récupération jobs orphelins)
├── config.py        # Settings pydantic (préfixe APP_, lit .env)
├── db.py            # SQLite : executer/interroger async, WAL, verrou threading
├── models.py        # Contrats Pydantic LLM (Correction, PannePhase, AlerteDetectee, DeltaRelecture…)
├── schema.sql       # Schéma complet (projets, parametres, chapitres, codex, codex_index,
│                    #  journaux, alertes, analyses, corrections)
├── llm/             # client.py (compatible OpenAI), prompts.py (anti-injection), mock.py (tests)
├── services/        # normalisation.py, reconciliation.py, chaine.py, alertes.py,
│                    #  analyse.py (orchestrateur jobs), rendu.py (document annoté)
├── routes/web.py    # Écrans E1/E3/E4/E5
├── templates/       # base.html, index.html, analyses/*.html
└── static/          # style.css, app.js, vendor/ (htmx, alpine — NE PAS MODIFIER)
tests/               # pytest : unit + intégration (mock LLM), 85 tests
scripts/tester_llm.py  # ping fail-fast des 5 modèles (utilise le vrai .env)
```

## Git
- Remote : `https://github.com/calogerovolpe/correction-app` (dépôt **privé**), branche `master`
- Identité de commit : `calogerovolpe <bx.volpe@gmail.com>`
- **Un commit par jalon ou correctif** (message : `Jn — <contenu> — N tests verts`),
  push systématique après commit
