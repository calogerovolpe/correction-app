# Progression — jalons, état, décisions

> Dernière mise à jour : 2026-09-09 (jalon F3 livré — Atelier E5 en Svelte + API `/api/v1` ; prochain jalon = F4).

## État des jalons

| Jalon | Statut | Commit |
|---|---|---|
| J0 — Socle technique | ✅ Terminé | `4102ada` |
| J1 — Moteur métier | ✅ Terminé | `28f7b62` |
| J2 — MVP de relecture | ✅ Terminé (E2E réel Mistral) | `aa1d5f9` |
| J2.1 — Correctifs retour utilisateur | ✅ Terminé | `569c784` |
| J2.2 — Atelier interactif & Fidélité Word | ✅ Terminé | `22b7639` |
| J2.3 — Catégorisation déclarative | ✅ Terminé | `cbc9cd2` |
| J2.4 — Rendu texte riche & fiabilisation bulle | ✅ Terminé | `0bb9577` |
| Memory Bank — source de vérité unique | ✅ Terminé | `cce00cc` |
| **J2.5 — Atelier v2 (texte courant, couches, clic droit)** | ✅ **Terminé (E2E réel Mistral)** | `05bcbda` |
| **A — Fiabilité du cœur (ids uniques, no-op, menu fiable)** | ✅ **Terminé** | `b5545f0` |
| Memory Bank — réorganisation du plan (R1/R2 refonte rendu-état + UX1→UX4) | ✅ Terminé | `fac3463` |
| Memory Bank — découpage R1 en R1-a/R1-b (deux conversations, handoff) | ✅ Terminé | `a4dfe98` |
| **R1-a — Onglets UI + projection par phase (rendu seul)** | ✅ **Terminé** | `245071b` |
| **R1-b — Stockage par phase + déduplication affichage (fin `CorrectionFusionnee`)** | ✅ **Terminé (E2E réel Mistral)** | `c911547` |
| **R2 — Base immuable + annotations (fin du remappage d'offsets)** | ✅ **Terminé (E2E réel Mistral)** | `e886d3a` |
| **F0 — Socle** (Vite+Svelte+TS, design tokens, layout, routage, coquille accueil, client fetch, `.gitignore`) | ✅ **Terminé** | `4cbb55c` |
| **F1 — Accueil & projets E1** (`/api/v1/projets`, création, activation, suppression + protection, analyses récentes, états vides) | ✅ **Terminé** | `cb6abc1` |
| **F2 — Soumission E3 + suivi E4** (`/api/v1/analyses`, collage Word, matrice dérogable, compteur 30 000, polling, fail-fast visible) | ✅ **Terminé (E2E réel Mistral adapté au `/api/v1`)** | `6cdfb22` |
| **F3 — Atelier E5** (couches, onglets + compteurs, menu riche [UX1], édition + « ↻ Re-corriger » [UX4], toggle [UX2], validation, navigation clavier) | ✅ **Terminé** | `023534a` |
| **FA1 — Intégrité ré-ancrage & non-perte de texte** (reconstruction, patch/édition) | ⬜ **Prochain jalon** | — |
| **FA2 — Identité documentaire & cycle de vie** (IDs uniques document, purge choix, réévaluation parallèle) | ⬜ À faire | — |
| **FA3 — Segmentation atomique aux bornes** (rendu, multi-marques, document complet non tronqué) | ⬜ À faire | — |
| **FA4 — Rendu Svelte fidèle & styles réels** (couleurs réelles, formatage Word, toggle opérationnel, onglet stable) | ⬜ À faire | — |
| **FA5 — Robustesse LLM** (Custom Structured Outputs, budget tokens, finish_reason, prompts/explications) | ⬜ À faire | — |
| **FA6 — Cohérence transactionnelle** (révision état atelier, concurrence, contrats /api/v1 alignés) | ⬜ À faire | — |
| **FA7 — Restitution pédagogique** (diff avant/après, sidebar sticky, popover accessible, clavier fluide) | ⬜ À faire | — |
| **F4 — Finitions UX & identité** (toasts, responsive, microcopy, AA complet) | ⬜ En attente (après FA7) | — |
| **F5 — Nettoyage & bascule** (retrait Jinja2/HTMX/Alpine, spec+README+patterns à jour, E2E `/api/v1`, `.bat`) | ⬜ En attente (après F4) | — |
| J3 — Chaîne séquentielle & Codex narratif | ⬜ En attente (après F5) | — |
| J4 — Confort | ⬜ À faire | — |
| J5 — Mise en ligne | ⬜ À faire | — |

**Tests : 159/159 verts** (`pytest`, dont **28 tests d'intégration TestClient/MockLLM sur `/api/v1/`** — 17 F2 + 11 F3 atelier) + **45 tests Vitest** (frontend Svelte) + E2E réel Mistral rejoué au jalon F2 (soumission/suivi via `/api/v1/`).

> **Absorption UX1→UX4 (2026-09-09)** : la roadmap de refonte frontend **F0→F5** absorbe UX1→UX4 (UX1 → F3 ; UX2 → F4 layout + F3 toggle ; UX3 → F1 ; UX4 → F3) — ils ne seront plus exécutés séparément. Source de vérité : `plan-refonte-frontend.md`.

## Ce qui marche (validé de bout en bout)

- Soumission d'un texte (Chapitre/Passage/Extrait) avec éditeur Word-fidèle, ping fail-fast, pipeline 3 phases parallèles via Mistral, suivi asynchrone HTMX (E4), analyses récentes sur l'accueil, récupération des jobs orphelins.
- **Atelier E5 (F3, Svelte)** : écran `#/atelier/{id}` — couches superposables (Forme rouge, Style pointillé bleu, Technique fond jaune), onglets par phase + compteurs, barre latérale, toggle « masquer », **menu contextuel riche** au clic droit (marque : Appliquer/Garder l'original ; sélection : Embellir/Alternative), **édition directe** du paragraphe + « ↻ Re-corriger », **validation du texte affiché**, navigation clavier — alimenté par `GET /api/v1/analyses/{id}/atelier` + actions JSON.
- **Atelier v2 (J2.5)** : document annoté en couches superposables (Forme rouge, Style bleu, Technique fond jaune), état courant matérialisé (texte affiché = version de travail), corrections Forme appliquées par défaut et refusables, embellissement & alternatives par sélection + clic droit (réévaluation du paragraphe), « Soumettre une nouvelle version » (texte courant repris), « Valider la version actuelle » (texte affiché + hash + backup natif + chaîne N+1), « Soumettre un autre texte » avec configurations mémorisées, navigation clavier.

## Détail des jalons livrés (historique migré de l'ancien journal de bord)

- **J0** : squelette FastAPI + Jinja2, schéma SQLite complet (renommé sessions→projets), page d'accueil E1 (création de projets, projet actif), Docker + compose, `.env.example`, 11 tests de schéma (contraintes, CASCADE, trigger RESTRICT, idempotence).
- **J1** : cœur métier sans UI, 100 % testé — `normalisation.py` (CRLF/BOM, paragraphes base 1, offsets tranches Python), `reconciliation.py` (ancre `contexte_avant`, rejets individuels, PannePhase, liste vide jamais une panne, déduplication Style prioritaire), `chaine.py` (machine N+1, refus zéro token), `alertes.py` (numérotation MAX+1 stable), client LLM + mock.
- **J2** : écran E3 (soumission, matrice de phases, forçage Passage/Extrait, remplacement officiel, garde-fou taille), jobs asynchrones HTMX (E4), phases 3-6 parallèles via Mistral (fail-fast, Option B), document annoté E5 — 80 tests verts + E2E réel Mistral sur un vrai chapitre.
- **J2.1** : fix redirection systématique vers `/analyses/1` (bug `rowcount` vs `lastrowid` — régression couverte par test), cases pré-cochées dérogables (matrice = pré-sélection), jauge de créativité Embellissement, analyses récentes sur l'accueil, récupération des jobs orphelins — 85 tests verts.
- **J2.2** : éditeur Word-fidèle (`texte_riche.py`, runs `RunFormat`, respect des paragraphes), barre latérale droite E5, Style/Embellissement à la demande (bulles popover, `POST /api/alternatives`), Technique latéral, validation finale manuelle (« Soumettre une nouvelle version » / « Valider la version actuelle ») — 89 tests verts.
- **J2.3** : nettoyage strict au collage Word (`o:p`, `&nbsp;`, `<br>`), fin de la détection automatique (catégorie choisie par l'utilisateur), numéro pré-rempli N+1, règle « dernier validé gagne », case opt-in mise à jour Codex/Journaux.
- **J2.4** : rendu E5 réparé (`parser_document_riche`), styles Word restitués dans les segments non corrigés, bulles fiabilisées via `dataset`, nettoyage en profondeur des paragraphes/runs fantômes.
- **J2.5 (atelier v2)** — décision de l'auteur, refonte guidée par ses retours :
  - **3 bugs bloquants réparés** : (1) « Soumettre une nouvelle version » = squelette (`pass`) + déballage `rowcount/lastrowid` → `/analyses/1` ; (2) bouton « Valider » jamais affiché (vocabulaire de `decision` changé en J2.3 sans suivre le template) ; (3) validation enregistrant le texte original au lieu de la version choisie ;
  - **état courant matérialisé** : table `documents`, service pur `reconstruction.py` (splices + remappage déterministe, localisation ancrée), routes E5 déplacées dans `app/routes/atelier.py` ;
  - **couches superposables** : `rendu.py` réécrit (plus de blocs « multi ») ; Technique visible dans le texte (fond jaune) ET en barre latérale ;
  - **Embellissement & alternatives par sélection + clic droit** : plus une phase de soumission (jauge E3 supprimée) ; embellissement → réévaluation LLM du paragraphe ; bouton « ↻ Réévaluer » ; fin des bulles au clic gauche ;
  - **validation du texte affiché** (Chapitres, confirmation JS) + **backup natif SQLite** + rotation ; « Soumettre un autre texte » (Passage/Extrait) avec E3 pré-cochée ;
  - navigation clavier branchée (`app.js` réécrit), branches mortes supprimées, config/docstrings alignées Mistral, README pointeur, `.bat` committé — 99 tests verts + E2E réel Mistral.
- **A — Fiabilité du cœur** (correctifs UX, décision 33-34, commit `b5545f0`) :
  - **ids de correction uniques** : nouveau service pur `reconciliation.renumeroter()` — réassignation globale déterministe `c-0001…` après `dedupliquer()` (les ids émis par chaque phase LLM pouvaient se doubler → même `data-groupe`, barre latérale désynchronisée, choix Forme collés) ;
  - **no-op Forme rejetés** : `extraire_corrections` écarte individuellement toute entrée Forme où `original == correction` (« cous » → « cous ») ; Style/Technique NON concernés (marquage sans réécriture légitime) ;
  - **menu contextuel fiable** : CSS `[hidden] { display: none !important }` (la règle `.menu-contextuel { display: flex }` neutralisait le `hidden`), menu + popover en `position: fixed` avec `clientX/clientY` (robuste au scroll, recentrage), popover positionné à l'écran, fermeture clic extérieur / Échap effective ;
  - 9 tests de régression — 108 tests verts.
- **R1-a — Onglets hybrides + projection par phase** (commit `245071b`) : `preparer_document_par_phase` (filtre les `entrees` puis réutilise `preparer_document`), routage `onglet` (GET query + champ caché des POST + route `/analyses/{id}/onglet` sans mutation d'état), barre d'onglets `Tout | Forme | Style | Technique` (+ Embellissement conditionnel), retrait des pastilles/`.filtre-*-off` ; zéro token LLM en plus — 116 tests verts.
- **R1-b — Stockage par phase + déduplication d'affichage** (commit `c911547`) : fin de `CorrectionFusionnee`/`EmbellissementMigre` (code mort), `dedupliquer()` SUPPRIMÉE — en recouvrement (exact ou partiel), Style et Embellissement coexistent (déduplication = règle d'affichage) ; `renumeroter()` sur `list[Correction]` ; `corrections.data_json` en dict par phase ; renommage complet `entree["fusion"]` → `entree["correction"]` — 114 tests verts + E2E réel Mistral rejoué.

## Reste à faire (priorisé)

> Ordre détaillé, étapes, architecture cible et design system : **`plan-refonte-frontend.md`** (roadmap maîtresse F0→F5, créée le 2026-09-09).
> **Les jalons UX1→UX4 de `plan-correctifs-atelier-ux.md` sont ABSORBÉS par F0→F5** (UX1 → F3 ; UX2 → F4 layout + F3 toggle ; UX3 → F1 ; UX4 → F3) — ils ne seront plus exécutés séparément. R1/R2 sont LIVRÉS et ne sont plus à réaliser.

1. **F1 — Accueil & projets E1** : ✅ **LIVRÉ** (`cb6abc1`).
2. **F2 — Soumission E3 + suivi E4** : ✅ **LIVRÉ** (`6cdfb22`).
3. **F3 — Atelier E5** : ✅ **LIVRÉ** (`023534a`) — API atelier JSON + écran Svelte `#/atelier/{id}` (couches, onglets + compteurs, menu riche **[UX1]**, édition directe + « ↻ Re-corriger » **[UX4]**, barre latérale, toggle **[UX2]**, navigation clavier, validation), accent Technique AA ocre.
4. **F4 — Finitions UX & identité** : cohérence visuelle ; états vides ; toasts ; accessibilité/focus/contrastes/aria (vérification AA des nouvelles couleurs) ; responsive ; layout ~1200 px **[absorbe le reste d'UX2]** ; microcopy. **PROCHAIN JALON.**
3. **F3 — Atelier E5** : endpoints `/api/v1/analyses/{id}` ; couches superposables ; onglets par phase + compteurs ; menu contextuel riche **[absorbe UX1]** ; édition directe sans IA temps réel + « ↻ Re-corriger » **[absorbe UX4]** ; barre latérale ; toggle « masquer » **[absorbe la partie toggle d'UX2]** ; navigation clavier ; validation du texte affiché.
4. **F4 — Finitions UX & identité** : cohérence visuelle ; états vides ; toasts ; accessibilité/focus/contrastes/aria (vérification AA des nouvelles couleurs) ; responsive ; layout ~1200 px **[absorbe le reste d'UX2]** ; microcopy.
5. **F5 — Nettoyage & bascule** : retrait Jinja2/HTMX/Alpine + routes HTML inutiles ; spec + README + `systemPatterns`/`techContext` à jour ; E2E Mistral rejoué `/api/v1` ; lanceur `.bat` vérifié.
6. **J3 — Chaîne & codex** (EN ATTENTE, après F5) : écritures narratives (transaction, `avec_codex` câblé, codex/journaux), phase 2 LLM (extraction codex, cohérence, relecture-diff), écrans E2/E6/E7 + bandeau d'alertes, RAG alias.
7. **J4 — Confort** : E9 (backups liste/restauration/purge, exports md/docx, statistiques, logs debug), E8 (paramètres + test de connexion), import .docx (italique/gras), correction hors-ligne locale (candidat).
8. **J5 — Mise en ligne** : durcissement (auth simple), Caddy (TLS), compose production + volumes, sauvegardes programmées, doc de déploiement VPS, option Tailscale documentée.
9. **R3 — Extension des catégories** (futur) : une phase = une config + un onglet + une projection, zéro changement au cœur.

## Problèmes connus

- **121/121 tests verts** ; E2E réel Mistral OK (rejoué aux jalons R1-b et R2).
- **Au jalon F1** : 128/128 pytest + 19 Vitest verts (frontend Svelte).
- **Bugs constatés par l'auteur (correctifs — roadmap `plan-correctifs-atelier-ux.md`)** : ~~barre latérale désynchronisée (ids non uniques entre phases)~~ ✅ jalon A ; ~~corrections no-op (« cous » → « cous »)~~ ✅ jalon A ; ~~menu contextuel non fiable (`hidden` neutralisé, popover hors écran)~~ ✅ jalon A ; pas de menu contextuel sur une marque (jalon B) ; numéro attendu erroné pour un nouveau projet (jalon D).
- **Limite connue** : `_reevaluer_corrections` régénère des ids `c-r0001…` avec compteur remis à zéro par appel — deux réévaluations de paragraphes différents dans une même session peuvent théoriquement entrer en collision (même classe de bug que le jalon A, cas rare non constaté ; piste : séquence `c-r` continue à l'échelle du document).
- Dette (réduite au F3) : `app/routes/atelier.py` aminci (~259 lignes, logique extraite dans `app/services/atelier.py` ~390 lignes) — fractionnement fin (par écran) planifié pendant J3 si croissance (règle 300 lignes).

## Historique des décisions clés

- **A1-A9** (cahier des charges, figés dans la spec consolidée §11) : FastAPI/SQLite/Mistral/Jinja2+HTMX/Alpine, local-first, mono-utilisateur…
- **J2.1** : matrice de phases = pré-sélection dérogable ; jauge de créativité ; analyses récentes ; récupération jobs orphelins.
- **J2.2** : barre latérale à la place des tooltips ; Style/Embellissement à la demande ; validation manuelle des écritures narratives.
- **J2.3** : catégorisation déclarative (fin de la détection auto) ; « dernier validé gagne » sans blocage.
- **J2.5 (arbitrages de l'auteur, révisent J2.1/J2.2)** : validation du texte AFFICHÉ (chapitres, confirmation) ; Embellissement à la demande (fin de la jauge à la soumission) ; alternatives par sélection + clic droit (fin des bulles au clic gauche) ; couches superposables (Technique fond jaune dans le texte) ; « Soumettre un autre texte » avec configurations mémorisées ; backup natif à la validation. Détail : spec §11 décisions 27-32.
- **Refusés par l'auteur** (ne pas réouvrir) : chunking, échappement backticks, toggle d'affichage du texte complet.
- **2026-09-07** : Memory Bank source de vérité unique ; **J2.5** atelier v2.
- **2026-09-09** : série de correctifs atelier & confort UX arbitrée (roadmap `plan-correctifs-atelier-ux.md` ; spec §11 décisions 33-38 ; révise la décision 24) ; J3 mis en attente.
- **2026-09-09 (réorganisation)** : après arbitrage « refonte rendu/état » avec l'auteur, la roadmap est RÉORGANISÉE — ex-B/C/D/E deviennent UX1/UX2/UX3/UX4 et s'intercalent avec deux refontes : **R1** (onglets hybrides + stockage des corrections par phase + déduplication devenue règle d'affichage — révisant la décision 29 « couches superposables ») et **R2** (base immuable + annotations/patches : fin du remappage d'offsets dans `reconstruction.py`). Ordre imposé : R1-a → R1-b → UX1 → UX2 → UX3 → R2 → UX4 → J3 → J4 → J5 (UX3 intercalable). Rationale : chaque phase LLM produit déjà SA collection de corrections indépendante — c'est le RENDU qui fusionnait ; les onglets n'ajoutent aucun appel LLM (zéro token). Cible : « base immuable + annotations + projections ». Détail : `plan-correctifs-atelier-ux.md` (« Architecture cible ») et `activeContext.md` (décisions).
- **2026-09-09 (R1-a)** : **onglets hybrides + projection par phase LIVRÉS** (`245071b`, 116 tests verts) — `preparer_document_par_phase` (rendu), routage `onglet` (GET query + POST Form + route `/analyses/{id}/onglet`), barre d'onglets `Tout | Forme | Style | Technique` (+ `Embellissement` conditionnel), retrait des pastilles/`.filtre-*-off` ; spec §8.2/§8.3/§11 décision 29 révisée dans le même commit. **Stockage et `dedupliquer()` intacts (état intermédiaire volontaire — handoff « À LA FIN de R1-a » dans le plan) ; prochain jalon = R1-b, AUTRE conversation.**
- **2026-09-09 (R1-b)** : **stockage par phase + déduplication d'affichage LIVRÉS** (`c911547`, 114 tests verts + E2E réel Mistral rejoué) — fin de `CorrectionFusionnee`/`EmbellissementMigre` (code mort), `dedupliquer()` supprimée (recouvrement exact Style/Embellissement → les DEUX coexistent), `renumeroter()` sur `list[Correction]`, `corrections.data_json` en dict par phase, renommage complet `entree["fusion"]` → `entree["correction"]` ; spec §3/§4.4/§7.1/§11 décision 29 dans le même commit. **Le handoff R1-a est CONSOMMÉ ; prochain jalon = UX1.**
- **2026-09-08 (R2)** : **base immuable + annotations LIVRÉES** (`e886d3a`, 121 tests verts + E2E réel Mistral rejoué OK) — fin du « texte mutable + remappage d'offsets » : état `documents` = base (texte normalisé immuable) + corrections en coordonnées de la base (jamais décalées) + choix/refus + patches manuels ; « texte courant » = projection calculée ; refuser une Forme = un filtre ; réévaluation ré-ancrée sur la base (Forme appliquées → patches) ; migration des états antérieurs à la volée (choix préservés par id, modifs manuelles abandonnées — décision) ; spec §4.1/§8.2/§8.3/§11 décisions 28 (révisée) et 39 dans le même commit. **R2 livré en avance (décision de l'auteur) ; prochain jalon = UX1.**
- **2026-09-09 (F0)** : **socle frontend Svelte livré** (`4cbb55c`, 121 pytest + 7 Vitest verts, `svelte-check` 0 erreur) — `frontend/` (Vite + Svelte 5 + TypeScript) versionné avec `package-lock.json` ; design tokens (thème + couches de correction réelles) ; layout global + routage hash ; page d'accueil coquille servable (build → `app/static/spa/`, gitignoré) ; client fetch typé `/api/v1/` (prêt F1) ; `.gitignore` étendu (`frontend/node_modules/`, `frontend/dist/`, `app/static/spa/`). **Backend intact (121 pytest) ; l'application tourne toujours en Jinja2/HTMX/Alpine ; prochain jalon = F1.**
- **2026-09-09 (F1)** : **Accueil & projets E1 LIVRÉS** (`cb6abc1`, 128 pytest + 19 Vitest verts, `svelte-check` 0 erreur) — `app/routes/api.py` (routeur `/api/v1`, aucune logique métier dupliquée) : `GET/POST /api/v1/projets` (création, premier projet actif), `POST /api/v1/projets/{id}/activer` (UPSERT, un seul actif), `DELETE /api/v1/projets/{id}` (cascade totale ; projet actif → 409, trigger SQL garantie ultime), `GET /api/v1/analyses` (10 récentes, extrait 60 car.) ; **accueil Svelte branché** (`Accueil.svelte` : liste, création, activation, suppression avec confirmation via `Modale.svelte`, analyses récentes cliquables, états vides) servi à `/` quand le build existe (repli Jinja2 sinon — `web.py`) ; `vite.config.ts` `base '/static/spa/'` ; composants `Bouton`/`Badge`/`Modale` + module `lib/api/projets.ts` ; **tests E1 Jinja2 migrés vers l'API + Vitest** (l'accueil n'est plus rendu par Jinja2) ; spec §2.1/§2.2/§8.2 dans le même commit. **Backend métier intact (pipeline, fail-fast, Option B, base immuable) ; prochain jalon = F2.**
- **2026-09-09 (F2)** : **Soumission E3 + suivi E4 LIVRÉS** (`6cdfb22`, 145 pytest dont 17 tests d'intégration `/api/v1/` + 42 Vitest, `svelte-check` 0 erreur ; E2E réel Mistral adapté au `/api/v1` rejoué OK) — `GET /api/v1/soumission` (projet actif, numéro N+1, dernières options, max_caractères), `POST /api/v1/analyses` (équivalent JSON du POST Jinja2 : refus explicites 400 — texte vide, trop long sans troncature, aucune phase, aucun projet actif — puis job `analyse.executer(id)` référencé dans `_TACHES`), `GET /api/v1/analyses/{id}` (statut/étape/erreur + synthèse `resultat` lecture seule pour `terminee`, étendue en F3) ; **écrans Svelte** `#/soumission` (`EditeurWord` + `lib/editeur/nettoyage.ts` : nettoyage Word strict, sérialisation v2 identique au Jinja2, matrice de phases dérogable, compteur 30 000) et `#/analyses/{id}` (`Suivi.svelte` : polling 2 s, statuts explicites, fail-fast visible, jamais de statut fantôme, lien « Ouvrir le résultat » vers E5) ; `App.svelte` + `NavBar` + `lib/api/analyses.ts` + composants `Bandeau`/`EditeurWord` ; spec §2.1/§2.2/§2.3/§8.2 dans le même commit. **Backend métier intact (pipeline, fail-fast, Option B, base immuable) ; prochain jalon = F3 — Atelier E5.**
- **2026-09-09 (F3)** : **Atelier E5 LIVRÉ** (`023534a`, 159 pytest dont 28 tests d'intégration `/api/v1/` (17 F2 + 11 F3) + 45 Vitest, `svelte-check` 0 erreur / 0 warning) — **logique atelier extraite** dans `app/services/atelier.py` (orchestration : état `documents`, `contexte_resultat` avec **compteurs par phase**, choix Forme, patches, embellissement **sans état partiel**, réévaluation, **édition directe**, suggestions, nouvelle version, validation) ; **API JSON atelier** `GET /api/v1/analyses/{id}/atelier?onglet=` (contrat `EtatAtelier`, lecture pure) + `POST …/choix-forme` `…/editer` `…/appliquer-alternative` `…/appliquer-embellissement` `…/reevaluer` `…/nouvelle-version` `…/valider` ; suggestions `POST /api/v1/embellir` / `POST /api/v1/alternatives` ; **écran Svelte `#/atelier/{id}`** (`Atelier.svelte` + `OngletsPhase` `DocumentAnnote` `BarreLaterale` `MenuContextuel` `PopoverSuggestion` `EditionParagraphe` `ToggleMasquer`, `lib/api/atelier.ts`, types F3) : couches réelles, onglets + compteurs, **menu contextuel riche** (marque OU sélection), barre latérale, toggle « masquer », navigation clavier, **édition directe + « ↻ Re-corriger »**, validation ; **accent Technique AA** ocre `#6e5400` (fin du violet — décision 40, spec §11) ; **`.bat` inchangé**.
- **2026-09-09 (Audit post-F3 & roadmap FA1→FA7 arbitrée)** : audit approfondi senior full-stack / LLM / UI-UX validé par l'auteur — mise en évidence des failles de ré-ancrage, segmentation, toggle et IDs. La série FA1→FA7 est actée comme priorité absolue avant F4 et F5. Prochain jalon = FA1.