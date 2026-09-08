# Contexte actif — où nous en sommes MAINTENANT

> Fichier le plus souvent mis à jour. Dernière mise à jour : 2026-09-08 (jalon R2 livré — base immuable + annotations, fin du remappage d'offsets ; prochain jalon = UX1).

## Focus du moment

**Série R1-a/R1-b → UX4 (refonte rendu/état + correctifs UX) — AVANT J3.**
La roadmap détaillée est dans **`plan-correctifs-atelier-ux.md`** (même dossier) : la RELIRE EN DÉBUT DE SESSION — elle contient l'ordre des jalons, leurs dépendances et l'architecture cible. Un commit par jalon ; le suivi (statut/commit) est tenu à jour dans ce plan ET dans `progress.md`.

- **Où on en est** : jalon A ✅ (`b5545f0`) ; réorganisation du plan ✅ (`fac3463`) ; découpage R1-a/R1-b ✅ (`a4dfe98`) ; R1-a ✅ (`245071b`) ; **R1-b ✅ (`c911547`) — Stockage par phase + fin de `CorrectionFusionnee`** ; **R2 ✅ (`e886d3a`) — Base immuable + annotations (fin du remappage d'offsets)** ; **prochain jalon = UX1 — Menu contextuel riche**.
- **R1 était DÉCOUPÉ en DEUX conversations** : R1-a (UI + rendu) ✅ puis R1-b (stockage par phase + fin de `CorrectionFusionnee`) ✅ — le handoff « À LA FIN de R1-a » du plan est CONSOMMÉ (section conservée pour l'historique).
- **Ordre imposé** : R1-a → R1-b → UX1 → UX2 → UX3 → R2 → UX4 → J3 → J4 → J5 (UX3 indépendant, intercalable). **R2 a été livré dès après R1-b** (décision de l'auteur : il ne dépend de rien d'autre que R1, et il est exigé AVANT UX4 et J3) — les jalons UX1/UX2/UX3 restent à faire dans l'ordre.
- R1 est CODÉ (R1-a rendu/UI ✅ + R1-b stockage par phase ✅) ; **R2 est CODÉ** (base immuable + annotations) : les corrections portent leurs offsets D'ORIGINE (base), plus AUCUN remappage — le « texte courant » est une projection calculée.

## État global

- Jalons terminés : **J2.5 — Atelier v2**, **A — Fiabilité du cœur**, **R1-a — Onglets hybrides**, **R1-b — Stockage par phase**, **R2 — Base immuable + annotations**.
- Tests : **121/121 verts** (`pytest`).
- **E2E réel Mistral OK** de bout en bout (`scripts/e2e_j25.py`, environnement isolé `data_e2e/`) : analyse 3 phases → nouvelle version (texte courant repris) → validation (chapitre officiel corrigé, hash, chaîne N+1, backup natif créé). — **rejoué au jalon R2**.
- Application validée de bout en bout avec Mistral Small.

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

1. **UX1 — Menu contextuel riche** (ex-B) : clic droit sur marque SANS sélection, choix Forme déplacé dans le menu, barre latérale lecture seule. **PROCHAIN JALON.**
2. **UX2 — Confort d'affichage** (ex-C) : toggle « masquer » (révise la décision 24), layout élargi ~1200 px, style des onglets (les pastilles ont disparu avec R1-a).
3. **UX3 — Navigation, projets** (ex-D) : activation — bug du « 2 » bloqué, navbar, suppression de projet avec confirmation + protection du projet actif. *Indépendant, intercalable à tout moment.*
4. **R2 — Base immuable + annotations (patches)** : refonte de `reconstruction.py`, fin du remappage d'offsets ; E2E requis (l'état est touché).
5. **UX4 — Édition directe sans IA temps réel** (ex-E) : texte éditable + « ↻ Re-corriger » ; dépend de R2.
6. **J3 — Chaîne & codex** (EN ATTENTE) : écritures narratives (transaction, `avec_codex` câblé, codex/journaux), phase 2 LLM (extraction codex, cohérence, relecture-diff), écrans E2/E6/E7 + bandeau d'alertes, RAG alias. Ne démarre qu'APRÈS R2 (la validation officielle lit l'état courant). Critère d'acceptation : Prologue → ch.1 → ch.2 → resoumission N=N sans remplacement → remplacement officiel (relecture-diff) → alerte → « Choix d'auteur » → non re-détectée.
7. **J4 — Confort** puis **J5 — Mise en ligne** (inchangés) ; **R3 — extension des catégories** (futur : une phase = une config + un onglet + une projection, zéro changement au cœur).

## Décisions en cours / à arbitrer

- **Refonte rendu/état arbitrée (2026-09-09) — NOUVELLES DÉCISIONS** (détail : `plan-correctifs-atelier-ux.md`, « Architecture cible ») :
  1. **Onglets hybrides** : « Tout » (vue superposée actuelle, conservée) + un onglet par phase (`Forme | Style | Technique | Embellissement si suggestions`) — **RÉVISE la décision 29 « couches superposables »** ; remplace les pastilles-filtres cumulables.
  2. **Stockage par phase** ✅ (R1-b) : collections de corrections indépendantes par phase (fin du JSON fusionné unique de la table `corrections`) ; `renumeroter()` conservé (jalon A).
  3. **Déduplication = règle d'affichage** ✅ (R1-b) : l'Embellissement n'est plus *absorbé* dans le tooltip du Style ; les deux coexistent (superposés dans « Tout », séparés dans leurs onglets).
  4. **Base immuable + annotations/projections (R2)** ✅ (`e886d3a`) : remplace « texte mutable + remappage d'offsets » de `reconstruction.py` — la validation officielle et « Soumettre une nouvelle version » lisent la PROJECTION.
  5. **Multi-passes conservé** : 3 appels LLM parallèles, texte complet chacun ; les onglets ne changent RIEN aux tokens (zéro appel LLM ajouté/supprimé).
  6. **R1 découpé en R1-a / R1-b** (DEUX conversations distinctes) : R1-a = UI onglets + projection par phase (rendu seul — stockage et `dedupliquer` intacts) ; R1-b = stockage par phase + suppression de `CorrectionFusionnee`/`embellissement_migre` (code mort : aucune correction `embellissement` n'est produite par le pipeline, l'embellissement est à la demande). Handoff d'état intermédiaire documenté dans le plan (« État du code À LA FIN de R1-a ») — CONSOMMÉ : R1-a `245071b` ✅ et R1-b `c911547` ✅.
- Anciennes décisions arbitrées (2026-09-09) : spec §11 **décisions 33-38** (ids de correction uniques, rejet des no-op, toggle « masquer » — **RÉVISE la décision 24**, menu contextuel riche, suppression de projet, édition sans IA temps réel) — voir `plan-correctifs-atelier-ux.md`.
- Précision d'implémentation du jalon A (décision 34) : le rejet des no-op ne concerne que la **phase Forme** — Style/Technique marquent SANS réécrire (`original == correction` y est le mode de marquage légitime, ex. fond jaune Technique).
- Migration des analyses antérieures ARBITRÉE (2026-09-08, jalon R2) : re-parsing depuis `analyses.texte_source` + `corrections.data_json`, choix/refus préservés par id, modifications manuelles abandonnées — livré en `e886d3a`.
- Décisions antérieures figées : `projectbrief.md` (+ spec §11 décisions 1-32) ; historique : `progress.md`.

## Dettes / anomalies connues (documentation)

- **Limite connue (jalon A, hors des 3 bugs)** : `_reevaluer_corrections` (`atelier.py`) régénère des ids `c-r0001…` avec un compteur remis à zéro à CHAQUE appel — deux réévaluations de paragraphes DIFFÉRENTS dans la même session peuvent théoriquement produire le même id (même classe de collision que le bug 1). Cas rare, non constaté ; à traiter si l'atelier le révèle (piste : continuer la séquence `c-r` à l'échelle du document).
- `app/routes/atelier.py` (~400 lignes) > cible 300 : le fractionnement fin (par écran) reste planifié pendant J3 si le fichier grossit encore (règle systemPatterns n° 8).
- Le déballage `(lastrowid, rowcount)` est documenté comme piège — un commentaire de garde figure sur le seul site restant (`nouvelle-version`).