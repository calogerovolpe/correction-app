# Plan — Refonte frontend : Svelte 5 + TypeScript + Vite (roadmap maîtresse F0→F5)

> Créé le 2026-09-09.
> À relire en début de CHAQUE session, avec toute la memory-bank/.
> Ce plan est LA source de vérité de la série F0→F5 : cocher les jalons terminés
> et mettre à jour `activeContext.md` / `progress.md` après chaque session.
> **Un jalon = UNE conversation ; la conversation suivante repart de la Memory Bank.**

## Objectif

Remplacer le frontend **Jinja2 + HTMX + Alpine.js** par **Svelte 5 + TypeScript +
Vite**, compilé en statique et servi par FastAPI, avec une identité visuelle
cohérente et **accessible** pour une primo-romancière non développeuse
(persona indicatif **« Camille »** — nom générique de persona, pas un prénom figé).

Cette roadmap **ABSORBE les jalons UX1→UX4** de `plan-correctifs-atelier-ux.md`
(voir « Correspondance ») : UX1 à UX4 ne seront plus exécutés séparément.
Le backend métier (services purs, pipeline LLM, schéma) est INTACT — seule la
couche de présentation évolue.

## État de départ

- **R1-a (`245071b`), R1-b (`c911547`) et R2 (`e886d3a`) sont livrés.**
- **121/121 tests pytest verts** ; E2E réel Mistral rejoué OK
  (`scripts/e2e_j25.py`, isolé `data_e2e/`).
- Modèle d'état : **base immuable + annotations + projections** (R2) — le frontend
  Svelte consommera ces projections, le cœur n'est pas touché.
- Frontend actuel : **Jinja2 + HTMX + Alpine.js TOUJOURS ACTIF**, migré
  progressivement (routes conservées jusqu'à F5).
- **Backend intouché** par la refonte.

## Révision de décision (à acter)

Cette roadmap RÉVISE la **décision A2** du cahier des charges (« Jinja2 + HTMX +
Alpine.js, pas de build Node ») et la **spec consolidée §2.1** (stack frontend
« décisions figées », reprise en **§11 décision 25**). La révision n'est PAS
encore codée : l'application tourne TOUJOURS en Jinja2/HTMX/Alpine au moment de
cette rédaction. La bascule Svelte est PLANIFIÉE et sera répercutée dans la spec
+ `systemPatterns.md` + `techContext.md` AU FIL des jalons (F0 pour l'amorce,
F5 pour la bascule finale). Ne décrire AUCUN état de code non encore réalisé
comme acquis.

## Règles invariables

- **Local-first** : aucun CDN, aucune police distante, aucune télémétrie.
- **pytest 121 verts + tests frontend Vitest verts** à chaque jalon.
- **Ne pas affaiblir ni supprimer un test existant** pour le faire passer.
- Ne pas toucher : `.env`, `data/`, `app/schema.sql`, `app/services/*`,
  `app/llm/*`, `app/db.py` (`app/models.py` seulement si besoin validé par
  l'auteur).
- Ne pas modifier le **pipeline LLM** (3 phases parallèles, fail-fast, Option B,
  « liste vide = jamais une panne »).
- **Couches de correction** : reprendre les couleurs RÉELLEMENT affichées
  (voir DESIGN SYSTEM ci-dessous) ; **WCAG AA partout** (≥ 4.5:1 texte courant,
  ≥ 3:1 grands textes / composants de surface).
- **Manuscrit en serif, interface en sans-serif**, polices système locales ;
  **microcopy 100 % française** ; taille de base **≥ 16px**, interligne confortable.
- **Mode Plan d'abord** → feu vert de l'auteur avant de coder.
- **Un jalon = une conversation** ; la conversation suivante repart de la
  Memory Bank.

## Architecture cible & choix techniques

- **Stack** : Svelte 5 + TypeScript + Vite ; build `frontend/` → `app/static/spa/`.
- **Versionnage** : **`frontend/` SEUL** ; `app/static/spa/`,
  `frontend/node_modules/`, `frontend/dist/` **gitignorés** — ajout au jalon F0.
- **Serving** : FastAPI sert `app/static/spa/` et expose une **API JSON sous
  `/api/v1/`** réutilisant les **services purs existants** (aucune logique
  métier dupliquée).
- **Bascule** : routes **Jinja2 conservées jusqu'à F5** — bascule incrémentale :
  un écran Jinja2 n'est retiré que lorsque son équivalent Svelte le couvre
  entièrement.
- **Tests frontend** : **Vitest**.

## DESIGN SYSTEM (source : `app/static/style.css` — ne PAS réinventer les couches)

### Couches de correction (telles qu'AFFICHÉES aujourd'hui)

| Couche | Texte | Fond | Note |
|---|---|---|---|
| Forme | `#c62828` | `#fdecea` | — |
| Style | `#1565c0` | `#e3f2fd` | — |
| Technique | `#212121` | `#fff9c4` (fond du marquage, `--fond-technique-mark`) | contraste AA ≈ 15:1 — déjà en place ; l'ancien accent violet `--corr-technique: #6a1b9a` est **OBSOLÈTE** et sera remplacé, au jalon F3, par un accent accessible cohérent avec le jaune (à valider AA), **sans jamais changer le fond jaune du marquage** |
| Embellissement | `#2e7d32` | `#e8f5e9` | — |

### Thème (identité visuelle à introduire)

- `--fond-page: #F6F1E9` ; `--fond-surface: #FFFDF8` ; `--encre: #2A2622` ;
  `--encre-douce: #6E665E` ; `--accent: #8A3B2C` ; `--accent-fonce: #6E2D21` ;
  `--accent-doux: #F3E0D8` ; `--bordure: #E4DCD0` ; `--succes: #3E6B4F` ;
  `--erreur: #B3402A` ; `--attention: #A36B1E`.
- Toute paire de couleurs utilisée doit respecter **WCAG AA**
  (vérification au F4).

### Typographie (système, locale, accessible)

- **Interface** : `system-ui, -apple-system, "Segoe UI", Roboto,
  "Helvetica Neue", Arial, sans-serif`.
- **Manuscrit** : `Georgia, "Times New Roman", serif`.

### Composants

Boutons (primaire / secondaire / tertiaire / danger), carte, badge de phase,
onglets, barre latérale, menu contextuel, panneau d'annotations, toast,
état vide, modale, indicateur de progression, bouton « ↻ Re-corriger », toggle.

## Correspondance avec l'ancien plan (absorption UX1→UX4)

| Ancien jalon | Absorbé par | Détail |
|---|---|---|
| UX1 — Menu contextuel riche | **F3** | menu contextuel de l'atelier |
| UX2 — Confort d'affichage | **F4** (layout) + **F3** (toggle « masquer ») | layout ~1200 px / responsive ; toggle en F3 |
| UX3 — Navigation, projets | **F1** | accueil & projets E1 |
| UX4 — Édition directe sans IA temps réel | **F3** | édition + « ↻ Re-corriger » |

Les jalons **UX1→UX4** de `plan-correctifs-atelier-ux.md` sont **ABSORBÉS par
F0→F5 et ne seront plus exécutés séparément.**

## Suivi des jalons

| Jalon | Contenu | Statut | Commit |
|---|---|---|---|
| F0 | Socle : Vite+Svelte+TS, design tokens, layout global, routage, page d'accueil coquille, client fetch typé ; MAJ `.gitignore` (`spa/`, `node_modules/`, `dist/` gitignorés) | ✅ | `4cbb55c` |
| F1 | Accueil & projets E1 : endpoints `/api/v1/projets`, création, activation, suppression avec confirmation + protection du projet actif, analyses récentes, états vides | ✅ | `cb6abc1` |
| F2 | Soumission E3 + suivi E4 : endpoints `/api/v1/analyses`, collage Word fidèle, catégorie, numéro N+1, matrice de phases dérogable, compteur 30 000 car., statuts explicites, polling, fail-fast visible | ✅ | `6cdfb22` |
| F3 | Atelier E5 : endpoints `/api/v1/analyses/{id}`, couches superposables, onglets par phase + compteurs, menu contextuel riche **[absorbe UX1]**, édition directe sans IA temps réel + « ↻ Re-corriger » **[absorbe UX4]**, barre latérale, toggle « masquer », navigation clavier, validation du texte affiché | ✅ | `023534a` |
| F4 | Finitions UX & identité : cohérence visuelle, états vides, toasts, accessibilité/focus/contrastes/aria (vérification AA des nouvelles couleurs), responsive, layout ~1200 px **[absorbe UX2]**, microcopy | ✅ | `74d602e` |
| F5 | Nettoyage & bascule : retrait Jinja2/HTMX/Alpine et routes HTML inutiles, spec + README + `systemPatterns`/`techContext` à jour, E2E Mistral rejoué (adapté à `/api/v1`), lanceur `.bat` vérifié | ⬜ | — |

## Jalon F0 — Socle

> ✅ **LIVRÉ** (commit `4cbb55c`) — socle Vite + Svelte 5 + TS, design tokens,
> layout, routage, coquille servable, client fetch ; backend intact (121 pytest) ;
> 7 tests Vitest verts ; `svelte-check` 0 erreur.

1. **Scaffolding** : `frontend/` (Vite + Svelte 5 + TypeScript), build dirigé vers
   `app/static/spa/` ; **MAJ `.gitignore`** : `app/static/spa/`,
   `frontend/node_modules/`, `frontend/dist/` — **`frontend/` est versionné SEUL**.
2. **Design tokens** : variables du thème (voir DESIGN SYSTEM) + couches de
   correction RÉELLES ; typographies interface/manuscrit ; base ≥ 16px ;
   interligne confortable.
3. **Layout global + routage** : shell Svelte (barre de navigation, contenu,
   pied) ; page d'accueil **coquille** (non branchée à l'API).
4. **Client fetch typé** : module TS orienté `/api/v1/` (types + fonctions),
   prêt pour F1.
5. **Vitest** : configuration + premiers tests de smoke (rendu coquille, tokens).

### État du code À LA FIN de F0

- App FastAPI inchangée (Jinja2/HTMX/Alpine toujours par défaut).
- `frontend/` versionné ; la coquille compilée est **servable** par FastAPI sous
  `/spa/` mais PAS encore câblée comme écran principal.
- Backend intact ; `.gitignore` à jour (aucun environnement de build commité).

## Jalon F1 — Accueil & projets E1

> ✅ **LIVRÉ** (commit `cb6abc1`) — endpoints `/api/v1/projets` (liste,
> création, activation, suppression avec confirmation + protection du projet
> actif) et `/api/v1/analyses` (10 récentes) ; accueil Svelte branché servi à
> `/` quand le build existe (repli Jinja2 sinon) ; backend intact (128 pytest) ;
> 19 tests Vitest verts ; `svelte-check` 0 erreur.

1. **Endpoints `/api/v1/projets`** : GET liste, POST création, POST activation,
   DELETE avec suppression TOTALE en cascade + protection du projet actif
   (comportement métier INTACT, réutilise les services existants).
2. **Écran accueil Svelte** : liste des projets, création, activation,
   **suppression avec confirmation**, **analyses récentes** cliquables,
   **états vides** avec microcopy française.
3. **Vitest** : composants + client fetch (mocked).

### État du code À LA FIN de F1

- Accueil Svelte couvre E1 ; le template Jinja2 `index.html` ne peut être
  neutralisé que si la couverture de E1 est TOTALE (sinon conservé jusqu'à F5).
- Aucun changement du pipeline LLM ni des services métier.

## Jalon F2 — Soumission E3 + suivi E4

> ✅ **LIVRÉ** (commit `6cdfb22`) — endpoints `/api/v1/analyses` (POST
> soumission, GET `{id}` statut/suivi) + `/api/v1/soumission` (préparation E3) ;
> écrans Svelte E3 (`#/soumission` : collage Word fidèle, catégorie, numéro
> N+1, matrice dérogable, compteur 30 000) et E4 (`#/analyses/{id}` : statuts
> explicites, polling 2 s, fail-fast visible) ; refus explicites 400 inchangés ;
> backend intact (145 pytest) ; 42 tests Vitest ; `svelte-check` 0 erreur ;
> E2E réel Mistral rejoué (soumission/suivi via `/api/v1`).

1. **Endpoints `/api/v1/analyses`** : POST soumission, GET statut/suivi,
   lecture du résultat — réutilise le moteur de jobs asynchrones INTACT.
2. **Collage Word fidèle** (nettoyage au collage, comme aujourd'hui) ;
   **catégorie** (Chapitre / Passage / Extrait) ; **numéro N+1** pré-rempli ;
   **matrice de phases dérogable** ; **compteur 30 000 caractères** visible.
3. **Suivi E4** : **statuts explicites**, **polling**, **fail-fast visible**
   (jamais de statut fantôme).
4. **Tests d'intégration TestClient/MockLLM sur `/api/v1/`** (premier jalon qui
   l'exige) + Vitest.
5. **E2E réel Mistral adapté** : soumission/suivi branchées sur `/api/v1/`
   → rejoué.

### État du code À LA FIN de F2

- Soumission + suivi Svelte couvrent E3/E4 : routes hash `#/soumission` et
  `#/analyses/{id}` (accueil F1 inchangé, lien « Ouvrir le résultat » vers
  l'atelier E5) ; l'atelier E5 reste en Jinja2 (inchangé) jusqu'à F3.
- Le **résultat** `terminee` exposé par `GET /api/v1/analyses/{id}` est une
  synthèse lecture seule (nb corrections par phase) — contrat pensé pour être
  étendu par le payload complet de l'atelier au jalon F3.
- Pipeline LLM, Option B, fail-fast, « liste vide = jamais une panne »,
  base immuable : INTACTS.

## Jalon F3 — Atelier E5

> ✅ **LIVRÉ** (commit `023534a`) — l'atelier E5 est servi par le SPA Svelte
> (route `#/atelier/{id}`) contre l'API JSON `/api/v1` ; la logique métier est
> extraite dans **`app/services/atelier.py`** (partagée avec les routes Jinja2,
> conservées jusqu'à F5 — aucune duplication) ; UI : couches superposables,
> onglets par phase + compteurs, **menu contextuel riche** **[UX1]**, barre
> latérale, toggle « masquer », navigation clavier, **édition directe sans IA
> temps réel + « ↻ Re-corriger »** **[UX4]**, validation du texte affiché ;
> **accent Technique AA** ocre `#6e5400` (fin du violet obsolète, décision 40) ;
> 159 pytest + 45 Vitest verts ; `svelte-check` 0 erreur / 0 warning.

1. **Endpoints `/api/v1/analyses/{id}` (atelier)** : état courant (base +
   annotations/projections), choix Forme, alternatives, embellissement,
   réévaluation, édition directe, « ↻ Re-corriger », validation du texte affiché.
2. **Rendu annoté** : **couches superposables** (couleurs RÉELLES),
   **onglets par phase + compteurs**, **menu contextuel riche** **[absorbe UX1]**,
   **barre latérale**, **toggle « masquer les paragraphes sans correction »**,
   **navigation clavier**, **édition directe sans IA temps réel +
   « ↻ Re-corriger »** **[absorbe UX4]**, **validation du texte affiché**.
3. **Accent Technique (F3)** : remplacer l'ancien accent violet `#6a1b9a`
   OBSOLÈTE par un accent accessible cohérent avec le jaune du marquage
   (à valider AA) **sans jamais changer le fond jaune (`#fff9c4`)**.
4. Tests d'intégration `/api/v1/` + Vitest.

### État du code À LA FIN de F3

- L'atelier Svelte couvre E5 : route `#/atelier/{id}`, `GET /api/v1/analyses/{id}/atelier`
  + actions JSON (`choix-forme`, `editer`, `appliquer-alternative`,
  `appliquer-embellissement`, `reevaluer`, `nouvelle-version`, `valider`) et
  suggestions `POST /api/v1/embellir` / `POST /api/v1/alternatives` ; le SPA ne
  consomme plus les routes Jinja2 de l'atelier — **elles restent en place
  (délèguent à `app/services/atelier.py`) jusqu'à la bascule F5**.
- UX1 et UX4 sont ABSORBÉS ; la partie « toggle » d'UX2 est en place ;
  l'accent Technique AA ocre remplace le violet obsolète (décision 40).

## Prochain jalon à lancer

> ✅ **F4 — Finitions UX & identité LIVRÉ** (`74d602e`, 2026-09-10) — la pause de sécurité ouverte après l'audit post-F3 est LEVÉE (série FA1→FA7 achevée puis F4 livré).
> **Le prochain jalon de travail est F5 — Nettoyage & bascule** : retrait de Jinja2/HTMX/Alpine et des routes HTML inutiles, adaptation de `scripts/e2e_j25.py` à l'API JSON `/api/v1`, mise à jour de la spec consolidée + README + `systemPatterns.md` + `techContext.md`, lanceur `.bat` vérifié.

## Jalon F4 — Finitions UX & identité

> ✅ **LIVRÉ** (commit `74d602e`, 2026-09-10) — 203 pytest + 83 Vitest verts
> (73 + 10 nouveaux, `tests/toasts.test.ts`), `svelte-check` 0 erreur /
> 0 warning, SPA recompilée ; frontend seul (aucun changement backend/LLM →
> pas d'E2E Mistral requis).

1. **Cohérence visuelle** sur tous les écrans F0→F3 (thème appliqué partout).
2. **États vides** systématiques ; **toasts** ; **accessibilité** : focus,
   contrastes, aria, navigation clavier — **vérification AA des nouvelles
   couleurs** (dont le nouvel accent Technique de F3).
3. **Responsive** + **layout ~1200 px** **[absorbe le reste d'UX2]**.
4. **Microcopy 100 % française** relue de bout en bout.

### État du code À LA FIN de F4

- **Toasts accessibles** : store `lib/toasts.ts` + `ConteneurToasts.svelte`
  monté une fois dans `App.svelte` ; deux zones live (`role="status"` polie /
  `role="alert"` assertive), auto-fermeture paramétrable + bouton de fermeture ;
  succès E1/E3/E5 migrés vers les toasts, erreurs actionnables restant inline.
- **Indicateur de chargement unifié** (`IndicateurChargement.svelte`,
  spinner CSS + `prefers-reduced-motion`) sur E1/E3/E4/E5.
- **États vides** : `EtatVide` illustré (`aria-hidden`) + CTA « Créer mon
  premier projet » (E1), repli toggle masquer et barre latérale « texte
  limpide » (E5).
- **A11y** : lien d'évitement « Aller au contenu principal » (focus
  programmatique, hash intact), `:focus-visible` global, emojis `aria-hidden`.
- **Audit AA documenté** : ratios de TOUS les tokens commentés dans
  `tokens.css` (accent Technique ocre `#6e5400` sur jaune `#fff9c4` ≈ 4.7:1,
  décision 40 validée).
- **Responsive** : mobile 360–768 px (en-tête E5 en colonne, actions étirées,
  onglets à défilement horizontal, actions projet en colonne) ; colonne de
  lecture manuscrite ~75ch.
- Identité visuelle cohérente, accessible, responsive ; parité fonctionnelle
  complète avec Jinja2 en vue de la bascule.

## Jalon F5 — Nettoyage & bascule

1. **Retrait de Jinja2/HTMX/Alpine** et des **routes HTML devenues inutiles**
   (vérifier qu'aucun écran n'est à moitié couvert).
2. **Spec consolidée à jour** (§2.1 stack, §8 écrans, §11 décision 25 revue)
   + **README** + `systemPatterns.md` / `techContext.md` (la refonte y devient
   un FAIT, plus une planification).
3. **E2E réel Mistral rejoué**, adapté à `/api/v1` (au plus tard ici) ;
   `scripts/e2e_j25.py` (basé HTML Jinja2) **adapté pour cibler l'API JSON** ;
   **lanceur `.bat` vérifié**.
4. Parité E2E complète vérifiée avant bascule définitive.

### État du code À LA FIN de F5

- Frontend 100 % **Svelte 5 + TypeScript**, compilé en statique, servi par
  FastAPI ; plus de Jinja2/HTMX/Alpine de rendu ; backend métier INTACT.

## Règle de fin de jalon

1. **pytest 121 verts** + **tests Vitest verts** + (dès F2) **tests
   d'intégration TestClient/MockLLM sur `/api/v1/`** verts.
2. MAJ `activeContext.md` + `progress.md` + cocher le jalon dans ce plan.
3. Commit **« Fx — contenu — N tests verts »** → push.
4. Si un **contrat métier** OU la **stack/architecture** change : MAJ de la
   spec consolidée (et de `systemPatterns.md` + `techContext.md` si leur
   contenu devient faux) **DANS LE MÊME COMMIT**.
5. **E2E réel Mistral** : rejoué/adapté à l'API `/api/v1` en **F2**
   (soumission/suivi branchées) et en **F5** (bascule finale) —
   `scripts/e2e_j25.py` (basé HTML Jinja2) doit être adapté pour cibler l'API
   JSON au plus tard en F5.

## Après le jalon F5

Reprendre **J3 — Chaîne séquentielle & Codex narratif** (spec §9), puis **J4 —
Confort**, puis **J5 — Mise en ligne**. Le backend métier n'a pas bougé : la
fonctionnalité J3 se branchera sur les mêmes services purs, désormais exposés
via `/api/v1/`.