# Patterns système — architecture, décisions techniques, pièges

> Dernière mise à jour : 2026-09-07 (J2.5). Spécification détaillée : `docs/Architecture application web — v1 (spécification consolidée).md`.

## Vue d'ensemble (flux de données)

```
Navigateur (Jinja2 + HTMX polling + Alpine.js — vendor local ; fetch pour l'atelier)
  → routes FastAPI : web.py (écrans E1/E3/E4) + atelier.py (E5 : état courant,
    choix Forme, alternatives/embellissement à la demande, réévaluation, workflow)
  → job asynchrone asyncio.create_task (référencé dans _TACHES)
  → analyse.executer(id) : en_attente → en_cours (normalisation, chaîne, fail_fast,
      phases Forme/Style/Technique, ecriture) → terminee | echec (Option B) | rejetee
  → services purs (normalisation, chaine, reconciliation, rendu, reconstruction,
      texte_riche)
  → llm/client.py (compatible OpenAI → API Mistral) — injectable via
      analyse._client_llm() (MockLLM en tests, aussi pour l'atelier)
  → db.py (SEUL point d'accès SQL ; SQLite WAL, asyncio.to_thread, threading.Lock ;
      sauvegarder() = backup natif avant écriture narrative)
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

- **Atelier v2 (J2.5)** : l'état courant du texte est matérialisé (table `documents`, service pur `reconstruction.py`) — le texte AFFICHÉ est la version validée/soumise ; corrections Forme appliquées par défaut, refusables ; toute modification = splice de runs avec remappage DÉTERMINISTE des corrections (après → décalées, intersectantes → couvrent le remplacement / deviennent obsolètes pour Forme, avant → inchangées) ; localisation des fragments par ancre (`contexte_avant + fragment`, sinon occurrence unique) ; embellissement → réévaluation LLM du SEUL paragraphe.
- **Couches superposables (J2.5) — EN COURS DE REMPLACEMENT (R1)** : rendu par classes CSS cumulées (`mark-style`, `mark-technique`, `refusee`) — jamais de bloc fusionné qui avale une correction ; Technique visible dans le texte ET en barre latérale. ⚠️ Révisé le 2026-09-09 : les couches ne subsisteront QUE dans l'onglet « Tout » (R1) ; chaque phase aura sa projection dédiée (onglet), et la déduplication Style/Embellissement deviendra une règle d'AFFICHAGE (plus de mutation de données dans `reconciliation.dedupliquer()`).
- **Refonte cible — onglets/projections + base immuable (R1/R2, arbitrée 2026-09-09)** :
  1. Le texte normalisé est une **base immuable** ; les corrections sont des **annotations/patches** en coordonnées de la base ; le « texte courant » est une **PROJECTION** (patches acceptés appliqués, triés) — fin du remappage d'offsets (R2) ;
  2. chaque phase LLM produit **sa collection indépendante** de corrections (stockage par phase, fin du JSON fusionné) ;
  3. le rendu est une **projection par phase** (onglet) + une projection « Tout » (superposition) — R1 ;
  4. ajouter une catégorie = une config de phase + un onglet + une projection, zéro changement au cœur (R3) ;
  5. les 3 appels LLM parallèles sont inchangés : les onglets n'ajoutent ni ne retirent aucun appel (zéro token).
  Ordre imposé : R1 avant UX1/UX2 ; R2 avant UX4 et J3 (la validation officielle lit l'état courant). Détail : `plan-correctifs-atelier-ux.md` (« Architecture cible » + jalons R1/R2).
- **Chaîne N+1** : déclarative (catégorie/numéro choisis par l'auteur, J2.3) ; « dernier validé gagne » ; jamais de blocage.
- **Réconciliation d'offsets** : ancre `contexte_avant`, rejets individuels, validation Pydantic, fences nettoyées ; **no-op Forme rejeté** (jalon A : `original == correction` en phase forme = rejet individuel — Style/Technique marquent SANS réécrire, donc `original == correction` y est légitime).
- **IDs de correction globaux uniques** (jalon A) : les ids `c-XXXX` émis par chaque phase LLM ne sont JAMAIS utilisés tels quels — `reconciliation.renumeroter()` réassigne une suite unique et déterministe après `dedupliquer()` (appelé par `analyse.py`), sinon `rendu.py` colle deux corrections sur le même `data-groupe` (barre latérale désynchronisée, choix Forme partagés).
- **Alertes** : numérotation MAX+1 stable, choix d'auteur, double barrière (`alertes.py`, prête pour J3).

## Pièges connus (leçons de bugs réels — NE PAS REFAIRE)

- **FastAPI + formulaires** : valeur vide → `None` (impossible de distinguer « décoché » d'« absent ») → champ caché unique JSON `phases` écrit par le JS (`nouveau.html`).
- **Jinja2 auto-échappe les apostrophes ET les accents dans `| tojson`** (`n'a` → `n&#39;a` ; « modifié » → `modifi\u00e9` dans le JSON) → jamais d'assertion contenant apostrophe ou accent sur du HTML rendu.
- **Déballage `lastrowid, rowcount = await db.executer(...)`** : relire deux fois l'ordre — le bug est revenu en J2.2 (redirection `/analyses/1`) ; un commentaire de garde figure sur le site restant (`atelier.py::nouvelle-version`).
- **Un bouton validé par un test HTTP direct peut être INVISIBLE dans l'UI** : le bouton « Valider » de J2.2 ne s'affichait plus après le changement de vocabulaire de `decision` (J2.3) — les tests passaient en appelant la route directement. Toujours tester le RENDU du template (J2.5).
- **Une fonctionnalité "livrée" peut être un squelette** : « Soumettre une nouvelle version » (J2.2) contenait un `pass` — couvrir chaque route par un test de bout en bout.
- **`TestClient` suit les redirections par défaut** (303 → 200) : passer `follow_redirects=False` pour affirmer une redirection.
- **Bases de test vierges** masquent les bugs d'identifiants → toujours tester les incrémentations (2 soumissions → 2 ids distincts).
- **Bulles/popovers** : passer par les attributs `dataset`/`data-*` (immunise contre guillemets/apostrophes des fragments).
- **`asyncio.Lock` se lie à sa première boucle** → verrou SQLite = `threading.Lock` (choix délibéré, ne pas changer).

## Chemins critiques (à surveiller)

- `app/routes/atelier.py` — E5 (état courant, clic droit, workflow) : ~400 lignes, fractionnement fin planifié pendant J3 si croissance (règle n° 8).
- `app/services/reconstruction.py` — état courant (splices + remappage déterministe) : cœur de la cohérence texte affiché ↔ version validée ; 100 % pur et testé.
- `app/routes/web.py` — E1/E3/E4 (allégé en J2.5, ~230 lignes).
- `app/db.py` — verrou `threading.Lock` (choix délibéré) ; `sauvegarder()` = backup natif avant écriture narrative.
- `app/main.py` — récupération des jobs orphelins au démarrage, ne jamais retirer.
- `app/schema.sql` — schéma de référence (table `documents` ajoutée en J2.5), évolutions idempotentes (`CREATE TABLE IF NOT EXISTS`) justifiées par la spec.
- `app/static/vendor/` — HTMX/Alpine locaux, intouchables.

## Conventions de code

- **Tout en français** : identifiants sans accents (accents admis dans chaînes/messages UI) ; docstring de module obligatoire référençant les sections de la spec ; typage complet (`str | None`, `list[dict]`) ; dataclasses/frozen pour le métier pur, Pydantic pour les contrats LLM.
- **CSS** : palette WCAG AA en variables CSS (`--corr-forme` etc.) — ne pas changer sans arbitrage.
- **JS** : IIFE systématiques, aucune variable globale ; Alpine.js pour l'état d'affichage (filtres, lecture Embellissement), HTMX pour le polling (`hx-trigger="every 2s"`).
- **Templates** : `{% extends "base.html" %}`, blocs `titre`/`contenu` ; autoescape ON partout.