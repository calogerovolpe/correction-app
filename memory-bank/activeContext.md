# Contexte actif — où nous en sommes MAINTENANT

> Fichier le plus souvent mis à jour. Dernière mise à jour : 2026-09-09 (jalon FA2 LIVRÉ — prochain jalon = FA3).

## Focus du moment

**Fiabilisation post-audit de l'Atelier E5 — série FA1→FA7 — AVANT F4, F5 et J3.**
La roadmap détaillée est dans **`plan-fiabilisation-post-audit.md`** (même dossier) : **LA RELIRE EN DÉBUT DE SESSION**.
RÈGLE MAÎTRESSE : **1 JALON = 1 CONVERSATION DISTINCTE.**
Ne JAMAIS enchaîner deux jalons dans la même session sans feu vert explicite de l'auteur.
**NOUVELLE RÈGLE (2026-09-09)** : à la fin de CHAQUE action, communiquer les commits GitHub réalisés (hash, intitulé) et confirmer le push — `systemPatterns.md` règle n° 9.

- **Où on en est** :
  - La série R est LIVRÉE — R1-a ✅ (`245071b`) ; R1-b ✅ (`c911547`) ; R2 ✅ (`e886d3a`).
  - Les jalons F0 à F3 sont LIVRÉS — F0 ✅ (`4cbb55c`) ; F1 ✅ (`cb6abc1`) ; F2 ✅ (`6cdfb22`) ; F3 ✅ (`023534a`).
  - **FA1 — Intégrité du ré-ancrage et non-perte de texte est LIVRÉ** ✅ (`76a0057`) — 162 pytest + 45 Vitest verts, `svelte-check` 0 erreur, **E2E réel Mistral rejoué OK** (`data_e2e/` réinitialisé : chapitre validé corrigé, chaîne `ok`, 1 backup).
  - **FA2 — Identité documentaire, cycle de vie, réévaluation parallèle + bouton « Ouvrir » est LIVRÉ** ✅ (`7405310`) — 170 pytest + 47 Vitest verts, `svelte-check` 0 erreur, **E2E réel Mistral rejoué OK** ; **purge des analyses de test #7 à #16 de `data/database.sqlite3`** (backup de sécurité `data/database.avant-purge-fa2.sqlite3` ; analyses 1–6 conservées).
  - **F4 (Finitions UX) et F5 (Nettoyage & bascule) restent en pause** jusqu'à l'achèvement de la série corrective FA1→FA7.
  - **Prochain jalon immédiat = FA3 — Segmentation atomique aux bornes et document complet.**

## Changements récents (FA2 — Identité documentaire, cycle de vie, réévaluation parallèle, bouton « Ouvrir »)

- **Identité documentaire** (`atelier.py`) : `_prochain_numero_reevaluation(etat)` — le compteur des ids de réévaluation est CONTINU à l'échelle du document (inspecte tous les `c-XXXX`/`c-rXXXX`) : plus aucune collision `c-r0001` entre deux réévaluations de paragraphes distincts, aucun id recyclé (pas de refus fantôme). 2 tests existants adaptés (`c-r0001` → `c-r0002` — comportement VOULU).
- **Cycle de vie** (`reconstruction.py`) : `remplacer_corrections_paragraphe` purge `etat["choix"]` des corrections retirées (plus de refus fantôme) ; l'obsolescence après modification manuelle est UNIFORME pour toutes les phases (Forme, Style, Technique intersectées).
- **Conflits dynamiques** (`reconstruction.py`) : `_resoudre_chevauchements_formes` est idempotent et réexécuté à chaque choix (`basculer_choix`) — une Forme REFUSÉE ne bloque plus personne ; une concurrente obsolète « pour chevauchement » est RÉACTIVÉE quand sa bloquante disparaît (les obsolescences « Fragment modifié manuellement » restent persistantes).
- **Réévaluation parallèle** (`atelier.py`) : `asyncio.gather` sur les phases actives (comme le pipeline d'analyse) — même nombre d'appels LLM, ids attribués dans l'ordre des phases (déterministe).
- **Bouton « Ouvrir » (demande de l'auteur)** : `Projet.derniere_analyse_id` (dernière analyse TERMINÉE, `app/routes/api.py` + `types.ts`) ; `Accueil.svelte` : bouton primaire « Ouvrir » par manuscrit → `#/atelier/{id}` (ou `#/soumission` si projet vierge), activation au passage ; les analyses récentes pointent vers `#/atelier/{id}` si terminées, `#/analyses/{id}` sinon (le lien hors-routeur-hash de F1 est corrigé).
- **Purge des données de test (demande de l'auteur)** : analyses #7 à #16 (et leurs `documents`/`corrections`) supprimées de `data/database.sqlite3` — `PRAGMA integrity_check = ok`, analyses 1–6 conservées ; copie de sécurité avant purge : `data/database.avant-purge-fa2.sqlite3`.
- **Tests** : +8 pytest (purge choix, obsolescence uniforme, réactivation dynamique ×2, ids continus, pas de recyclage, parallélisme par mesure de durée, `derniere_analyse_id` API) ; 2 tests existants adaptés au compteur continu ; +2 Vitest (bouton Ouvrir atelier / soumission) ; 1 test du lien analyses récentes adapté. **170 pytest + 47 Vitest verts**, `svelte-check` 0 erreur.
- **Spec** : §11 **décision 42** — même commit.
- **E2E réel Mistral rejoué OK** (`data_e2e/` réinitialisé) : analyse 3 phases → nouvelle version → validation (chapitre corrigé, chaîne `ok`, 1 backup).

## État global

- Jalons terminés : **J2.5 — Atelier v2**, **A — Fiabilité du cœur**, **R1-a — Onglets hybrides**, **R1-b — Stockage par phase**, **R2 — Base immuable + annotations**, **F0 — Socle**, **F1 — Accueil & projets E1**, **F2 — Soumission E3 + suivi E4**, **F3 — Atelier E5**, **FA1 — Intégrité du ré-ancrage**, **FA2 — Identité documentaire + « Ouvrir »**.
- Tests : **170/170 verts** (`pytest`) + **47 tests Vitest** (frontend Svelte) ; `svelte-check` 0 erreur / 0 warning.
- **E2E réel Mistral OK** de bout en bout (`scripts/e2e_j25.py`, environnement isolé `data_e2e/`) : **soumission + suivi via `/api/v1/` (F2)**, puis analyse 3 phases → nouvelle version (texte courant repris) → validation (chapitre officiel corrigé, hash, chaîne N+1, backup natif créé). — **rejoué au jalon F2**.
- Application validée de bout en bout avec Mistral Small.

## Changements récents (F3 — Atelier E5 Svelte + API `/api/v1`, commit `023534a`)

- **Logique atelier extraite** dans `app/services/atelier.py` (~390 lignes) : état
  `documents` (chargement + migration R2), `contexte_resultat` (document annoté +
  **compteurs par phase**), choix Forme, alternatives, embellissement **sans état
  partiel** (patch appliqué sur une copie, sauvé seulement après réévaluation OK),
  réévaluation, **édition directe** (`reconstruction.remplacer_texte_paragraphe` —
  patch de paragraphe entier ancré base, corrections/patches antérieurs retirés),
  suggestions à la demande, nouvelle version, validation officielle. `app/routes/atelier.py`
  aminci (~259 lignes) : délègue au service et rend le template (conservé jusqu'à F5).
- **API JSON atelier (F3)** — `app/routes/api.py` : `GET /api/v1/analyses/{id}/atelier?onglet=`
  (contrat `EtatAtelier` = document annoté + compteurs, lecture pure jamais de statut
  fantôme), `POST …/choix-forme`, `…/editer`, `…/appliquer-alternative`,
  `…/appliquer-embellissement`, `…/reevaluer`, `…/nouvelle-version` (→ `{nouvel_id}`),
  `…/valider` (→ `{ok, numero, titre, hash}`) ; suggestions `POST /api/v1/embellir` et
  `POST /api/v1/alternatives`. Erreurs métier → `ErreurAtelier` → HTTPException détaillée.
- **Écran Svelte `#/atelier/{id}`** (`Atelier.svelte` + `OngletsPhase`, `DocumentAnnote`,
  `BarreLaterale`, `MenuContextuel`, `PopoverSuggestion`, `EditionParagraphe`,
  `ToggleMasquer`, `lib/api/atelier.ts`, types F3) : couches réelles (del/ins rouge, mark-style,
  mark-technique fond jaune), onglets + compteurs, menu contextuel riche au clic droit
  (marque Forme : Appliquer / Garder l'original ; sélection : Embellir / Alternative), barre
  latérale, toggle « masquer », navigation clavier ←/→, édition directe + « ↻ Re-corriger »,
  validation ; `Suivi.svelte` → lien « Ouvrir le résultat » vers `#/atelier/{id}`.
- **Accent Technique AA** : l'ancien violet `#6a1b9a` est remplacé par l'ocre `#6e5400`
  (tokens Svelte + `app/static/style.css`) — fond jaune `#fff9c4` jamais changé ;
  spec §11 **décision 40**.
- **Tests** : 11 tests d'intégration `tests/test_api_atelier.py` (TestClient/MockLLM :
  lecture pure, projection onglet, choix Forme, édition, alternative, embellissement sans
  état partiel, réévaluation, suggestions, nouvelle version, validation) + 3 tests unitaires
  d'édition directe (`test_reconstruction.py`) + 3 Vitest atelier (`frontend/tests/atelier.test.ts`).
- **Spec** : §2.1 (stack + endpoints F3), §2.2 (service atelier), §2.3 (atelier JSON),
  §8.2-E5 (écran Svelte), §10 (série F0→F5), §11 décision 40 — même commit.

## Changements récents (F2 — Soumission E3 + suivi E4, commit `6cdfb22`)

- **API JSON `/api/v1/` étendue** (`app/routes/api.py`, mêmes règles : « aucune
  logique métier dupliquée », moteur de jobs asynchrones réutilisé tel quel) :
  `GET /api/v1/soumission` (projet actif, numéro N+1 attendu, dernières
  configurations mémorisées, `max_caracteres` — source unique du compteur),
  `POST /api/v1/analyses` (équivalent JSON du POST `/analyses` Jinja2 : refus
  explicites 400 — texte vide, dépassement sans troncature, aucune phase,
  aucun projet actif — puis job `analyse.executer(id)` référencé dans
  `_TACHES`), `GET /api/v1/analyses/{analyse_id}` (statut/étape/erreur pour le
  polling + synthèse `resultat` lecture seule pour `terminee`, étendue au F3).
- **Écran Svelte soumission E3** (`routes/Soumission.svelte`, route hash
  `#/soumission`) : éditeur Word-fidèle (`EditeurWord.svelte` +
  `lib/editeur/nettoyage.ts` — nettoyage strict au collage, sérialisation v2
  identique au template Jinja2), catégorie Chapitre/Passage/Extrait, numéro
  **N+1 pré-rempli** (indicateur « attendu par la suite »), **matrice de
  phases dérogable** (pré-coches par catégorie, mémoire des dernières options),
  **compteur 30 000 caractères** visible (refus explicite au-delà), bouton
  désactivé si texte vide, bandeaux `Bandeau.svelte` pour les refus 400.
- **Écran Svelte suivi E4** (`routes/Suivi.svelte`, route hash
  `#/analyses/{id}`) : **polling 2 s** (arrêt à l'état final), **statuts
  explicites** (badges `en_attente → en_cours → terminee | echec | rejetee`),
  **fail-fast visible** (gabarits verbatim), **jamais de statut fantôme**
  (statut inconnu → erreur ; `404` → bandeau), résultat `terminee` → synthèse
  par phase + lien « Ouvrir le résultat » vers l'atelier E5 (Jinja2, jusqu'à F3).
- **Intégration** : `App.svelte` routeur (union `/`, `/soumission`,
  `/analyses/{id}`), `NavBar` (lien « Soumettre un texte »), types +
  module typé `lib/api/analyses.ts`, composants `Bandeau`/`EditeurWord`,
  bouton « Réessayer » en cas d'échec de préparation.
- **Tests** : 17 tests d'intégration TestClient/MockLLM sur `/api/v1/`
  (`tests/test_api_analyses.py` — soumission, refus 400, matrices, fail-fast,
  Option B, 404, lecture pure, ids incrémentaux) + 23 tests Vitest
  (`editeur`, `apiAnalyses`, `soumission`, `suivi`) — 42 au total.
- **E2E réel Mistral adapté** (`scripts/e2e_j25.py`) : soumission + suivi
  branchés sur `/api/v1/` (les étapes atelier restent Jinja2) — **rejoué OK**.
- **Backend métier intact** : 145/145 pytest ; pipeline LLM, Option B,
  fail-fast, « liste vide = jamais une panne », base immuable : inchangés.
  Spécification §2.1/§2.2/§2.3/§8.2 mise à jour dans le même commit.

## Changements récents (F0 — Socle Svelte 5 + TypeScript + Vite, commit `4cbb55c`)

- **Scaffolding** — `frontend/` créé (Vite + Svelte 5 + TS ; `npm install` OK,
  `package-lock.json` versionné) ; `.gitignore` étendu (`frontend/node_modules/`,
  `frontend/dist/`, `app/static/spa/` — le SPA compilé n'est JAMAIS commité).
- **Design tokens** (`frontend/src/lib/styles/tokens.css`) : thème (identité
  visuelle) + couches de correction RÉELLES (`app/static/style.css`) ;
  typographies interface/manuscrit ; base 16px, interligne 1.6.
- **Layout global + routage** : `App.svelte` (NavBar, contenu, pied), routeur
  hash zéro-dépendance (`lib/router.ts`), page d'accueil **coquille** non
  branchée à l'API.
- **Client fetch typé** (`lib/api/`) : module TS orienté `/api/v1/`, prêt pour F1
  (le serveur n'expose pas encore l'endpoint).
- **Vitest** : 7 tests verts (coquille + client fetch) ; `svelte-check` 0 erreur —
  config : `environment: 'jsdom'` + `resolve.conditions: ['browser']` (Svelte 5 :
  sans 'browser', `mount()` indisponible — leçon à retenir).
- **Backend intact** : 121/121 pytest ; l'application tourne TOUJOURS en
  Jinja2/HTMX/Alpine ; coquille compilée servable sous `/static/spa/` (assets
  relatifs) mais PAS encore câblée comme écran principal.

## Changements récents (R2 — Base immuable + annotations, commit `e886d3a`)

- **Modèle d'état (R2)** — `reconstruction.py` réécrit : l'état `documents`
  devient `{modele: 2, base, corrections, choix, patches, modifies}`. La BASE
  (texte normalisé d'origine, runs) est IMMUABLE ; les corrections sont TOUTES
  exprimées en coordonnées de la base (JAMAIS décalées) ; « texte courant » =
  PROJECTION calculée (`projeter_paragraphes`, fragments texte/remplacements).
- **Refuser une Forme = un FILTRE** (`basculer_choix`) : plus aucun remappage.
- **Patches manuels** (`appliquer_modification`) : alternative/embellissement =
  remplacement ancré base ; les Forme actives intersectées deviennent
  obsolètes ; une sélection qui recouvre partiellement une zone déjà modifiée
  est REFUSÉE (`ZoneDejaModifiee`).
- **Réévaluation** (`remplacer_corrections_paragraphe`) : les corrections
  retournées par le LLM (texte courant) sont RÉ-ANCRÉES sur la base ; les Forme
  appliquées deviennent des patches (le texte corrigé reste affiché).
- **Rendu** — `rendu.py` : nouveau point d'entrée
  `preparer_document_depuis_etat(etat, onglet)` (projette depuis la base +
  annotations) ; la logique de segments reste unique.
- **Migration** — `migrer_ancien_format` : les états antérieurs (texte muté)
  sont migrés à la volée au chargement (`_charger_etat`) : base reconstruite
  depuis `analyses.texte_source`, corrections depuis `corrections.data_json`,
  choix/refus préservés par id, modifications manuelles abandonnées (décision).
- **Pipeline LLM inchangé** (3 passes parallèles, zéro token en plus) ; UI
  atelier inchangée (onglets R1-a conservés).
- **Tests** : `test_reconstruction.py` réécrit (offsets jamais décalés,
  projection, patches, migration) + test d'intégration migration atelier ;
  114 → **121 verts** + E2E réel Mistral rejoué (OK).

## Changements précédents (R1-b — Stockage par phase + fin de `CorrectionFusionnee`, commit `c911547`)

- **Modèles** — `models.py` : `CorrectionFusionnee` et `EmbellissementMigre` SUPPRIMÉS (code mort) ; tout le cœur travaille sur `Correction` direct.
- **Réconciliation** — `reconciliation.py` : `dedupliquer()` SUPPRIMÉE (décision consignée au commit : elle ne faisait plus rien d'utile — aucune correction `embellissement` n'est produite par le pipeline, l'embellissement est à la demande) ; `renumeroter(list[Correction]) -> list[Correction]` (ids globaux uniques/déterministes conservés — jalon A). **Déduplication = règle d'AFFICHAGE** : en recouvrement (exact ou partiel), Style et Embellissement COEXISTENT.
- **Stockage PAR PHASE** — `analyse.py` : `corrections.data_json` = dict `{"forme": […], "style": […], "technique": […]}` (valeurs = `Correction.model_dump()`) ; colonne inchangée (`schema.sql` documenté).
- **Lecture + état** — `atelier.py` : `_charger_fusion` → `_charger_corrections` (lit le dict par phase, l'aplatit en `list[Correction]`) ; `_reevaluer_corrections` produit des `Correction`. `reconstruction.py` : `etat_initial(list[Correction], …)`, RENOMMAGE MÉCANIQUE COMPLET `entree["fusion"]` → `entree["correction"]` (vérifié par grep : plus aucun « fusion » dans `app/`, hormis `_fusionner_runs` — fusion de runs de texte). `rendu.py` : mêmes accès renommés.
- **UI : AUCUN changement** (les onglets R1-a restent) ; pipeline LLM inchangé (3 passes parallèles, Option B, fail-fast, zéro token en plus).
- **Tests** : 3 tests de migration remplacés par la NOUVELLE règle (recouvrement exact → les deux coexistent), fixtures en `Correction`, `test_analyse` vérifie le dict par phase ; 116 → **114 verts**.
- **Spec** : §3 (table `corrections`), §4.4 (déduplication = règle d'affichage), §7.1 étape 6, arborescence `reconciliation.py`, §11 décision 29 — même commit.
- **E2E réel Mistral REJOUÉ et OK** (`scripts/e2e_j25.py`, `data_e2e/` réinitialisé) : analyse → nouvelle version (relit le nouveau format) → validation (chapitre corrigé, hash, chaîne N+1, backup).

## Changements précédents (R1-a — Onglets hybrides + projection par phase, commit `245071b`)

- **Projection par phase** — `rendu.py` : nouvelle fonction pure `preparer_document_par_phase(paragraphes, entrees, phase, choix, modifies=None)` : filtre les `entrees` sur `e["fusion"].correction.phase == phase` puis appelle la `preparer_document()` existante (AUCUNE duplication de la logique de segments). `preparer_document()` reste la projection « Tout ».
- **Routage de l'onglet** — `atelier.py` : `_contexte_resultat(..., onglet="tout")` choisit la projection ; `_onglet_valide()` retombe sur « tout » si la valeur est inconnue ; GET `page_analyse` lit `?onglet=` ; les POST `choix-forme`/`reevaluer`/`appliquer-alternative`/`appliquer-embellissement` reçoivent `onglet: str = Form("tout")` → on reste sur l'onglet après l'action ; NOUVELLE route POST `/analyses/{id}/onglet` (re-rend `_atelier.html`, AUCUN état modifié) ; `a_embellissement` calculé sur l'état COMPLET (sinon la projection ferait disparaître l'onglet).
- **UI onglets** — `_atelier.html` : la légende de pastilles-filtres devient une barre d'onglets `role="tablist"` `Tout | Forme | Style | Technique` (+ `Embellissement` seulement si une correction de cette phase existe) ; boutons `data-action="onglet" data-onglet="..."`, état actif `aria-selected` ; `#zone-atelier[data-onglet]` porte l'onglet actif ; champ caché `onglet` dans les formulaires « nouvelle-version » et « valider » ; section « Techniques » de la barre latérale : `x-show="correctionsTechniques.length > 0"` (les filtres Alpine n'existent plus).
- **JS** — `app.js` : clic onglet → `poster('/analyses/{id}/onglet', {onglet})` ; `ongletActif()` (lu sur `#zone-atelier`) est transmis aux POST `choix-forme`/`reevaluer`/`appliquer-*` ; logique Alpine `filtres` retirée.
- **CSS** — `style.css` : styles d'onglets (palette WCAG AA, actif = fond de la couleur de phase, texte blanc) ; suppression des règles orphelines `.legende`/`.pastille*`/`.bouton-lecture*`/`.filtre-*-off`/`.lecture-embellissement`.
- **Tests** : +8 (3 projections rendu, 5 intégration : barre rendue/`aria-selected`, `?onglet=` projection, onglet inconnu → Tout, POST onglet sans mutation d'état, choix Forme conserve l'onglet) ; 1 test adapté (`pastille--forme` → `onglet--forme`). **116/116 verts.**
- **Spec** : §8.2 (E5), §8.3 (comportement des onglets), §11 décision 29 révisée (« Couches superposables » → « Onglets hybrides ») — même commit.
- **NON TOUCHÉ (volontaire, c'est R1-b)** : stockage `corrections.data_json` (liste plate de `CorrectionFusionnee`), `_charger_fusion`, `dedupliquer()`/`embellissement_migre`, `CorrectionFusionnee`/`EmbellissementMigre`, pipeline LLM (3 passes parallèles inchangées — zéro token en plus).

## Changements récents (A — Fiabilité du cœur, commit `b5545f0`)

- **IDs de correction uniques** : chaque phase LLM émet ses ids sans coordination (deux corrections de phases différentes pouvaient partager `c-0001` → même `data-groupe`, barre latérale désynchronisée, choix Forme collés). Nouveau service pur `reconciliation.renumeroter()` : réassignation globale déterministe `c-0001…c-NNNN` après `dedupliquer()`, appelée par `analyse.py` avant l'écriture en base.
- **No-op Forme rejetés** : `reconciliation.extraire_corrections` écarte individuellement toute entrée Forme où `original == correction` (« cous » barré pour réécrire « cous »). ⚠️ Portée FORME uniquement : Style/Technique marquent SANS réécrire (`original == correction` y est légitime).
- **Menu contextuel fiable** : règle CSS `[hidden] { display: none !important }` (avant : `.menu-contextuel { display: flex }` neutralisait le `hidden` → menu toujours visible) ; menu et popover en `position: fixed` positionnés par `clientX/clientY` (robuste au scroll) avec recentrage ; popover de suggestion positionné à l'écran (avant : `absolute` sans `left/top` → hors écran) ; fermeture au clic extérieur et à Échap (déjà codée, désormais effective).
- 9 tests de régression (unitaires rendu/réconciliation/reconstruction + intégration analyse + rendu atelier).

## Changements récents (J2.5)

- **Bugs bloquants réparés** (hérités de J2.2/J2.3, invisibles aux tests précédents) :
  - « Soumettre une nouvelle version » était un **squelette non implémenté** (boucle `pass`) + déballage `rowcount`/`lastrowid` → redirection systématique `/analyses/1` (régression du piège J2.1) ;
  - le bouton « Valider la version actuelle » **ne s'affichait plus** (décisions J2.3 `chapitre/passage/extrait` vs tests `conforme/remplacement_officiel`) ;
  - la validation enregistrait le texte ORIGINAL au lieu de la version choisie.
- **Atelier v2** : état courant matérialisé (nouvelle table `documents`, nouveau service pur `reconstruction.py`) ; rendu en **couches superposables** (`rendu.py` réécrit — Technique désormais aussi dans le corps du texte, fond jaune) ; **sélection + clic droit** → « Embellir la sélection » (réévaluation du paragraphe via LLM) et « Trouver une alternative » (synonyme/champ lexical) ; bouton « ↻ Réévaluer » sur les paragraphes modifiés ; validation = texte affiché + **backup natif SQLite** + rotation ; « Soumettre un autre texte » avec E3 pré-cochée (mémoire des configurations dans `parametres`) ; corrections Forme appliquées par défaut, refusables ; branches mortes (`decision == 'conforme'…`, bandeau `reclassement_extrait`, tooltips `_cas.html`) supprimées ; navigation clavier réellement branchée (`app.js` réécrit, était mort) ; matrice E3 ramenée à 3 phases (jauge supprimée) ; fractionnement de fait : `web.py` (E1/E3/E4, ~230 lignes) + `atelier.py` (E5 + workflow, ~400 lignes).
- **Divers** : config/docstrings alignées sur « Mistral uniquement » ; README transformé en pointeur Memory Bank ; `Ouvrir Correction.bat` committé ; spec §5.3/§6.1/§8.2/§10/§11 (décisions 27-32) mise à jour dans le même commit.

## Prochaines étapes (ordre)

1. **Série FA1→FA7 — Fiabilisation post-audit de l'Atelier E5 (ROADMAP ACTIVE)** :
   - **FA1 — Intégrité du ré-ancrage et non-perte de texte (reconstruction)** : ✅ **LIVRÉ** (`76a0057`) ;
   - **FA2 — Identité documentaire, cycle de vie et réévaluation parallèle** : ✅ **LIVRÉ** (+ bouton « Ouvrir » des projets et purge des analyses de test #7–#16, demandes de l'auteur) ;
   - **FA3 — Segmentation atomique aux bornes et document complet** : ⬜ **PROCHAIN JALON IMMÉDIAT** (P0, bloquant) ;
   - **FA4 — Rendu Svelte fidèle, styles réels, formatage Word et robustesse UI** : ⬜ (P0/P1) ;
   - **FA5 — Robustesse LLM : Custom Structured Outputs, invariants et prompts** : ⬜ (P1) ;
   - **FA6 — Cohérence transactionnelle, concurrence et alignement d'API** : ⬜ (P1/P3) ;
   - **FA7 — Restitution pédagogique : diff, sidebar sticky, popovers et clavier** : ⬜ (P2).
2. **F4 — Finitions UX & identité** (MIS EN ATTENTE après FA7) : toasts, responsive, microcopy, AA complet.
3. **F5 — Nettoyage & bascule** (MIS EN ATTENTE après F4) : retrait Jinja2/HTMX/Alpine, E2E Mistral v1, spec consolidée.
4. **J3 — Chaîne & codex** (EN ATTENTE après F5) : écritures narratives, codex/journaux, alertes, relecture-diff.
5. **J4 — Confort** puis **J5 — Mise en ligne** (inchangés).

## Décisions en cours / à arbitrer

- **Refonte rendu/état arbitrée (2026-09-09) — NOUVELLES DÉCISIONS** (détail : `plan-correctifs-atelier-ux.md`, « Architecture cible ») :
  1. **Onglets hybrides** : « Tout » (vue superposée actuelle, conservée) + un onglet par phase (`Forme | Style | Technique | Embellissement si suggestions`) — **RÉVISE la décision 29 « couches superposables »** ; remplace les pastilles-filtres cumulables.
  2. **Stockage par phase** ✅ (R1-b) : collections de corrections indépendantes par phase (fin du JSON fusionné unique de la table `corrections`) ; `renumeroter()` conservé (jalon A).
  3. **Déduplication = règle d'affichage** ✅ (R1-b) : l'Embellissement n'est plus *absorbé* dans le tooltip du Style ; les deux coexistent (superposés dans « Tout », séparés dans leurs onglets).
  4. **Base immuable + annotations/projections (R2)** ✅ (`e886d3a`) : remplace « texte mutable + remappage d'offsets » de `reconstruction.py` — la validation officielle et « Soumettre une nouvelle version » lisent la PROJECTION.
  5. **Multi-passes conservé** : 3 appels LLM parallèles, texte complet chacun ; les onglets ne changent RIEN aux tokens (zéro appel LLM ajouté/supprimé).
  6. **R1 découpé en R1-a / R1-b** (DEUX conversations distinctes) : R1-a = UI onglets + projection par phase (rendu seul — stockage et `dedupliquer` intacts) ; R1-b = stockage par phase + suppression de `CorrectionFusionnee`/`embellissement_migre` (code mort : aucune correction `embellissement` n'est produite par le pipeline, l'embellissement est à la demande). Handoff d'état intermédiaire documenté dans le plan (« État du code À LA FIN de R1-a ») — CONSOMMÉ : R1-a `245071b` ✅ et R1-b `c911547` ✅.
- Anciennes décisions arbitrées (2026-09-09) : spec §11 **décisions 33-38** (ids de correction uniques, rejet des no-op, toggle « masquer » — **RÉVISE la décision 24**, menu contextuel riche, suppression de projet, édition sans IA temps réel) — voir `plan-correctifs-atelier-ux.md`.
- **Décision 40 ACTÉE (F3)** : accent Technique AA ocre `#6e5400` (fin du violet) + atelier E5 servi par le SPA contre l'API JSON `/api/v1` (logique `app/services/atelier.py`) — détail spec §11.
- Précision d'implémentation du jalon A (décision 34) : le rejet des no-op ne concerne que la **phase Forme** — Style/Technique marquent SANS réécrire (`original == correction` y est le mode de marquage légitime, ex. fond jaune Technique).
- Migration des analyses antérieures ARBITRÉE (2026-09-08, jalon R2) : re-parsing depuis `analyses.texte_source` + `corrections.data_json`, choix/refus préservés par id, modifications manuelles abandonnées — livré en `e886d3a`.
- Décisions antérieures figées : `projectbrief.md` (+ spec §11 décisions 1-32) ; historique : `progress.md`.

## Dettes / anomalies connues (documentation)

- ~~**Limite connue (jalon A, hors des 3 bugs)** : `_reevaluer_corrections` (`atelier.py`) régénère des ids `c-r0001…` avec un compteur remis à zéro à CHAQUE appel~~ — ✅ **RÉSOLUE au jalon FA2** : `_prochain_numero_reevaluation` garantit une suite continue à l'échelle du document.
- `app/routes/atelier.py` **aminci au F3** (~259 lignes) : la logique a été extraite dans `app/services/atelier.py` (orchestration) — le fractionnement fin (par écran) reste planifié pendant J3 si le fichier grossit encore (règle systemPatterns n° 8).
- Le déballage `(lastrowid, rowcount)` est documenté comme piège — un commentaire de garde figure sur le seul site restant (`nouvelle-version`).