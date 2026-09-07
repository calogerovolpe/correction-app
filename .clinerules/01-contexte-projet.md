# Contexte projet — LIRE EN PREMIER

## Qu'est-ce que ce projet ?
Application web **privée, mono-utilisateur** de correction de manuscrit littéraire
(Chapitre / Passage / Extrait). L'auteur soumet un texte, 4 phases LLM parallèles le
corrigent (Forme, Style, Technique, Embellissement), le résultat s'affiche en document
annoté interactif. Un codex narratif persistant (personnages, glossaire…) mémorise le
roman au fil des chapitres officiels (chaîne N+1 stricte).

## Documents de référence — source de vérité
1. **État actuel et prochaines étapes** : `.clinerules/00-ou-nous-sommes.md` (synthèse ultra-courte à consulter en premier).
2. **Journal de bord des jalons** : `.clinerules/README.md` (historique complet des validations et critères).
3. **Spécification consolidée de l'application** : `docs/Architecture application web — v1 (spécification consolidée).md`
   → **Source de vérité détaillée** (métier + applicatif + registre des décisions). À consulter de manière ciblée pour des questions d'architecture ou lors de nouveaux jalons.
4. **Documents historiques** (dans `docs/` aussi) :
   - `docs/Cahier des charges — Application web de correction de manuscrit.md` : conception initiale (remplacé par la spec consolidée) ;
   - Hors repo, dans le dossier grand-parent : `Architecture fonction correction de texte — v3/v4/v5/v6.md`.

## Carte de lecture par tâche (Économie de tokens)
Pour éviter de saturer le contexte avec des lectures inutiles, s'en tenir aux fichiers strictement nécessaires :

| Type d'intervention | Fichiers de règles à consulter | Code à inspecter / modifier |
|---|---|---|
| **Bug UI / Affichage** | `02-conventions-code.md` | `app/templates/`, `app/static/style.css`, `app/static/app.js` |
| **Bug Découpage / Normalisation** | `02-conventions-code.md` | `app/services/texte_riche.py`, `app/services/normalisation.py` |
| **Bug LLM / Prompts** | `02-conventions-code.md` | `app/llm/prompts.py`, `app/llm/client.py` |
| **Bug Pipeline / Job** | `02-conventions-code.md` | `app/services/analyse.py`, `app/services/reconciliation.py` |
| **Nouveau Jalon (ex: J3)** | `00-ou-nous-sommes.md` + section ciblée dans `docs/` | Selon le plan validé en amont |

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
├── services/        # normalisation.py, reconciliation.py, chaine.py, alertes.py, texte_riche.py,
│                    #  analyse.py (orchestrateur jobs), rendu.py (document annoté)
├── routes/web.py    # Écrans E1/E3/E4/E5
├── templates/       # base.html, index.html, analyses/*.html
└── static/          # style.css, app.js, vendor/ (htmx, alpine — NE PAS MODIFIER)
tests/               # pytest : unit + intégration (mock LLM), 77 tests
scripts/tester_llm.py  # ping fail-fast des 5 modèles (utilise le vrai .env)
```

## Git
- Remote : `https://github.com/calogerovolpe/correction-app` (dépôt **privé**), branche `master`
- Identité de commit : `calogerovolpe <bx.volpe@gmail.com>`
- **Un commit par jalon ou correctif** (message : `Jn — <contenu> — N tests verts`),
  push systématique après commit

