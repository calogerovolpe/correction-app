# Conventions de code

## Langue et style
- **Tout en français** : noms de fonctions/variables/docstrings/messages UI/commits (sans accents
  dans les identifiants Python ; accents admis dans les chaînes et messages utilisateur).
- Docstring de module obligatoire, **référençant les sections v6** concernées
  (ex. `"""Machine à états N+1 — v6 §6.5."""`). C'est le lien entre code et spécification.
- Typage : annotations complètes (`str | None`, `list[dict]`), dataclasses/frozen pour les
  valeurs métier pures, Pydantic pour les contrats LLM.

## Dimensionnement des fichiers et modularité
- **Cible de taille de fichier** : idéalement **< 300 lignes** de code par fichier.
- **Seuil d'alerte** : tout fichier approchant ou dépassant **500 lignes** doit faire l'objet d'un fractionnement lors du jalon suivant.
- **Règle de découpage** : par responsabilité métier / écran (ex: scinder un routeur en `analyses.py`, `resultat.py`, `projets.py`), jamais par découpage arbitraire de lignes.
- Ne pas sur-fractionner les petits modules : un service concis de 100 à 200 lignes est optimal.

## Architecture — règles fixes
1. **Services purs vs orchestration** : `normalisation.py`, `chaine.py`, `reconciliation.py`,
   `rendu.py` sont des fonctions PURES (testables sans DB ni LLM). `analyse.py` orchestre,
   `db.py` et `llm/` sont les seuls points d'accès externes.
2. **Client LLM injectable** : `analyse._client_llm()` est la fabrique ; les tests la
   remplacent par `MockLLM` via `monkeypatch`. Ne JAMAIS instancier `ClientLLM` ailleurs.
3. **Pas d'écriture SQL hors `app/db.py`** : utiliser `await db.executer(...)` /
   `await db.interroger(...)` (retour `(lastrowid, rowcount)` — ATTENTION à l'ordre,
   cf. bug J2.1).
4. **Verrou SQLite** : `threading.Lock` dans `db.py`, PAS `asyncio.Lock` (il se lie à sa
   première boucle d'événements — RuntimeError sur boucles multiples, bug réel rencontré).
5. **Jobs asynchrones** : `asyncio.create_task` référencé dans `_TACHES` (routes/web.py) ;
   `analyse.executer()` ne lève JAMAIS (statut final garanti) ; idempotence par
   `statut == 'en_attente'`.
6. **Échecs LLM** (v6 §8.5, §14.2) : entrée JSON invalide → rejet individuel SANS arrêt ;
   racine non parsable/non conforme → `PannePhase` → Option B (job `echec`, aucun résultat
   partiel) ; **une liste valide vide n'est JAMAIS une panne**.
7. **Rendu** : échappement par Jinja2 (autoescape activé) ; les identifiants de blocs
   `g-XXXX` sont calculés par Python (`rendu.py`), jamais demandés aux LLM.

## Pièges connus (leçons de bugs réels — ne pas les refaire)
- **FastAPI + formulaires** : une valeur de formulaire vide devient `None` pour un champ
  `str | None` → impossible de distinguer « décoché » d'« absent ». Solution en place :
  champ caché unique `phases` contenant un JSON d'état écrit par le JS (`nouveau.html`).
- **Jinja2 auto-échappe les apostrophes** (`n'a` → `n&#39;a`) → dans les tests, ne jamais
  faire d'assertion contenant une apostrophe sur du HTML rendu.
- **Bases de test vierges** masquent les bugs d'identifiants : toujours tester les
  incrémentations (2 soumissions → 2 ids distincts).
- **Déballage** `lastrowid, rowcount = await db.executer(...)` : relire deux fois l'ordre.

## CSS / JS / templates
- Palette WCAG AA définie en variables CSS (`--corr-forme` etc., v6 §7.2) — ne pas changer
  les couleurs sans arbitrage.
- JS : IIFE systématiques, aucune variable globale ; Alpine.js pour l'état d'affichage
  (filtres, lecture embellissement) ; HTMX pour le polling (`hx-get`/`hx-trigger="every 2s"`).
- Templates : `{% extends "base.html" %}`, blocs `titre`/`contenu` ; autoescape ON partout.
