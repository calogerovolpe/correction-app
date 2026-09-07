# Patterns système — architecture, décisions techniques, pièges

> Dernière mise à jour : 2026-09-07. Spécification détaillée : `docs/Architecture application web — v1 (spécification consolidée).md`.

## Vue d'ensemble (flux de données)

```
Navigateur (Jinja2 + HTMX polling + Alpine.js — vendor local)
  → routes FastAPI (app/routes/web.py : écrans E1/E3/E4/E5, POST /api/alternatives)
  → job asynchrone asyncio.create_task (référencé dans _TACHES)
  → analyse.executer(id) : en_attente → en_cours (normalisation, chaine, fail_fast, phases, ecriture)
      → terminee | echec (Option B) | rejetee (fail-fast / préconditions)
  → services purs (normalisation, chaine, reconciliation, alertes, rendu, texte_riche)
  → llm/client.py (compatible OpenAI → API Mistral) — injectable via analyse._client_llm (MockLLM en tests)
  → db.py (SEUL point d'accès SQL ; SQLite WAL, asyncio.to_thread, threading.Lock)
```

## Règles d'architecture FIXES

1. **Services purs vs orchestration** : `normalisation.py`, `chaine.py`, `reconciliation.py`, `rendu.py` = fonctions PURES (testables sans DB ni LLM) ; `analyse.py` orchestre ; `db.py` et `llm/` sont les seuls points d'accès externes.
2. **Client LLM injectable** : ne JAMAIS instancier `ClientLLM` ailleurs que via `analyse._client_llm()` (tests : monkeypatch → `MockLLM`).
3. **Pas de SQL hors `db.py`** : `await db.executer(...)` / `await db.interroger(...)` — retour `(lastrowid, rowcount)`, ATTENTION à l'ordre (bug J2.1).
4. **Verrou SQLite** : `threading.Lock` (PAS `asyncio.Lock` — il se lie à sa première boucle d'événements → RuntimeError). Choix délibéré.
5. **Jobs asynchrones** : `analyse.executer()` ne lève JAMAIS (statut final garanti) ; idempotence par `statut == 'en_attente'` ; récupération des jobs orphelins au démarrage (`main.py` — ne jamais retirer).
6. **Échecs LLM** : JSON individuel invalide → rejet individuel sans arrêt ; racine non parsable/non conforme → `PannePhase` → Option B (job `echec`, aucun résultat partiel) ; **une liste valide vide n'est JAMAIS une panne**.
7. **Rendu** : échappement par Jinja2 autoescape ; identifiants de blocs `g-XXXX` calculés par `rendu.py`, jamais demandés aux LLM.
8. **Dimensionnement** : cible < 300 lignes/fichier ; alerte à 500 → fractionner au jalon suivant, par responsabilité métier/écran (jamais arbitrairement).

## Patterns métier clés

- **Chaîne N+1** : conforme → chapitres ; N=N sans remplacement → Extrait ; N=N avec remplacement → officiel (préconditions `chaine.py`, refus zéro token) ; rupture → reclassement Extrait sans blocage.
- **Déduplication Style prioritaire** : recouvrement exact → migration en tooltip ; partiel → coexistence.
- **Réconciliation d'offsets** : ancre `contexte_avant`, rejets individuels, validation Pydantic, fences nettoyées.
- **Alertes** : numérotation MAX+1 stable, choix d'auteur, double barrière (`alertes.py`, prête pour J3).

## Pièges connus (leçons de bugs réels — NE PAS REFAIRE)

- **FastAPI + formulaires** : valeur vide → `None` (impossible de distinguer « décoché » d'« absent ») → champ caché unique JSON `phases` écrit par le JS (`nouveau.html`).
- **Jinja2 auto-échappe les apostrophes** (`n'a` → `n&#39;a`) → jamais d'assertion contenant une apostrophe sur du HTML rendu dans les tests.
- **Bases de test vierges** masquent les bugs d'identifiants → toujours tester les incrémentations (2 soumissions → 2 ids distincts).
- **Déballage** `lastrowid, rowcount = await db.executer(...)` : relire deux fois l'ordre.
- **Bulles d'alternatives** : passer par les attributs `dataset`/`data-*` (immunise contre guillemets/apostrophes des fragments).

## Chemins critiques (à surveiller)

- `app/routes/web.py` — à fractionner avant J3 (bug historique du déballage).
- `app/db.py` — verrou `threading.Lock`, choix délibéré.
- `app/main.py` — récupération des jobs orphelins au démarrage, ne jamais retirer.
- `app/schema.sql` — schéma de référence, évolutions idempotentes (`CREATE TABLE IF NOT EXISTS`) justifiées par la spec.
- `app/static/vendor/` — HTMX/Alpine locaux, intouchables.

## Conventions de code

- **Tout en français** : identifiants sans accents (accents admis dans chaînes/messages UI) ; docstring de module obligatoire référençant les sections de la spec ; typage complet (`str | None`, `list[dict]`) ; dataclasses/frozen pour le métier pur, Pydantic pour les contrats LLM.
- **CSS** : palette WCAG AA en variables CSS (`--corr-forme` etc.) — ne pas changer sans arbitrage.
- **JS** : IIFE systématiques, aucune variable globale ; Alpine.js pour l'état d'affichage (filtres, lecture Embellissement), HTMX pour le polling (`hx-trigger="every 2s"`).
- **Templates** : `{% extends "base.html" %}`, blocs `titre`/`contenu` ; autoescape ON partout.