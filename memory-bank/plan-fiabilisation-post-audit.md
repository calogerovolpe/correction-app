# Plan — Fiabilisation post-audit de l'Atelier (Roadmap maîtresse FA1→FA7 → F4 → F5)

> Créé le 2026-09-09 suite à l'audit approfondi de l'Atelier E5 (jalon F3).
> **RÈGLE MAÎTRESSE : 1 JALON = 1 CONVERSATION DISTINCTE.**
> Ne JAMAIS enchaîner deux jalons dans la même session sans feu vert explicite de l'auteur.
> À chaque début de conversation, lire `activeContext.md` et ce plan.
> Après chaque jalon terminé : tests verts → commit explicite → mise à jour `activeContext.md` + `progress.md` → handoff.

---

## 1. Contexte et objectif

L'audit senior full-stack / LLM / UI-UX réalisé après le jalon F3 (`023534a`) a mis en évidence que l'architecture « base immuable + annotations » est saine, mais que plusieurs **failles critiques et régressions réelles** menacent l'intégrité des manuscrits et la fidélité de l'atelier :
1. **Perte de texte possible à la réévaluation** : ré-ancrer une correction située à l'intérieur d'un patch manuel (ou d'une édition intégrale de paragraphe) remplace le patch entier par la correction.
2. **Segmentation tronquée** : le marquage Style/Technique s'applique au run Word entier plutôt qu'aux bornes exactes de l'annotation, et les marques multiples s'écrasent.
3. **Toggle inopérant** : le backend élimine les paragraphes propres avant l'envoi, rendant le masquage/démasquage client impossible.
4. **Collision d'identifiants** : le compteur `c-r0001…` remis à zéro par paragraphe casse l'unicité documentaire, les clés Svelte et les sélections.
5. **Couleurs et formatage neutralisés** : le CSS scoped des boutons écrase les couleurs des couches, et le gras/italique/souligné n'est pas rendu dans le DOM annoté.
6. **Contrats LLM trop lâches** : pas de Structured Outputs Mistral, pas de budget `max_tokens` de sortie, `finish_reason` ignoré.
7. **Saut d'onglet systématique** : les actions POST de l'atelier renvoient toujours la projection `tout`, rompant le flux de l'auteur.

La série **FA1→FA7** corrige ces failles dans un ordre strict de dépendance avant d'exécuter **F4 (Finitions UX & identité)** et **F5 (Nettoyage & bascule)**.

---

## 2. Tableau de bord des jalons

| Ordre | Jalon | Intitulé | Priorité | Risque | Statut | Commit |
|---|---|---|---|---|---|---|
| 1 | **FA1** | Intégrité du ré-ancrage et non-perte de texte (reconstruction) | P0 (Bloquant) | Élevé | ✅ **Livré** | *(voir `progress.md`)* |
| 2 | **FA2** | Identité documentaire, cycle de vie et réévaluation parallèle | P0/P1 (Majeur) | Moyen | ⬜ À faire | — |
| 3 | **FA3** | Segmentation atomique aux bornes et document complet (rendu) | P0 (Bloquant) | Moyen | ⬜ À faire | — |
| 4 | **FA4** | Rendu Svelte fidèle, styles réels, formatage Word et robustesse UI | P0/P1 (Majeur) | Moyen | ⬜ À faire | — |
| 5 | **FA5** | Robustesse LLM : Custom Structured Outputs, invariants et prompts | P1 (Majeur) | Moyen | ⬜ À faire | — |
| 6 | **FA6** | Cohérence transactionnelle, concurrence et alignement d'API | P1/P3 (Moyen) | Moyen | ⬜ À faire | — |
| 7 | **FA7** | Restitution pédagogique : diff, sidebar sticky, popovers et clavier | P2 (UX/a11y) | Faible | ⬜ À faire | — |
| 8 | **F4** | Finitions UX & identité (toasts, responsive, microcopy, AA complet) | F4 existant | Faible | ⬜ En attente (après FA7) | — |
| 9 | **F5** | Nettoyage final & bascule (retrait Jinja2/HTMX/Alpine, E2E v1) | F5 existant | Moyen | ⬜ En attente (après F4) | — |

---

## 3. Procédure détaillée par jalon (guide pour chaque conversation)

# Plan �P Fiabilisation post-audit de l'Atelier (Roadmap ma�tresse FA1→FA7 → F4 ▚ F5)

### Jalon FA1 — Intégrité du ré-ancrage et non-perte de texte (reconstruction)

- **Objectif** : Empêcher formellement qu'une correction issue d'une réévaluation ne détruise du texte hors de son emprise, en particulier après une édition directe ou un patch manuel existant.
- **Dépendances** : Aucune. C'est le prérequis absolu à toute utilisation sécurisée de l'atelier.
- **Fichiers à lire obligatoirement en début de session** :
  - `memory-bank/activeContext.md`
  - `memory-bank/systemPatterns.md`
  - `app/services/reconstruction.py`
  - `tests/test_reconstruction.py`
  - `tests/test_api_atelier.py`
- **Fichiers à modifier** :
  - `app/services/reconstruction.py` (`_convertir_vers_base`, `remplacer_corrections_paragraphe`, `remplacer_texte_paragraphe`, `appliquer_modification`)
  - `tests/test_reconstruction.py`
  - `tests/test_api_atelier.py`
- **Procédure exacte** :
  1. Écrire le test de régression échouant :
     - Créer un paragraphe `p-1` avec texte long.
     - Appliquer une édition directe complète via `remplacer_texte_paragraphe(etat, "p-1", "Texte entièrement réécrit par l'auteur.")`.
     - Simuler une réévaluation retournant une correction Forme sur un seul mot (`[6, 17)` -> « entièrement »).
     - Appeler `remplacer_corrections_paragraphe(etat, "p-1", [correction])`.
     - Vérifier que `texte_paragraphe(etat, "p-1")` **ne devient PAS uniquement le mot corrigé**, mais conserve l'intégralité du paragraphe réécrit avec la correction appliquée.
  2. Corriger la racine dans `app/services/reconstruction.py` :
     - `_convertir_vers_base()` : quand une coordonnée courante tombe strictement à l'intérieur d'un patch existant, interdire l'extension sauvage `d, f = frag["debut"], frag["fin"]` qui remplace toute la zone mère par une sous-plage.
     - Modèle de rebase de paragraphe : pour une édition directe de paragraphe complet, acter le modèle propre : le paragraphe édité devient la nouvelle base de référence du paragraphe (rebase de `base[pid]` ou patch composite à coordonnées locales stables) pour que les corrections futures s'y ancrent naturellement sans écrasement.
     - Sécuriser `remplacer_corrections_paragraphe` pour qu'une correction non ancrable soit proprement écartée et qu'une correction ancrable ne réduise jamais la portée des fragments environnants.
  3. Valider la non-régression des tests existants de réévaluation et d'embellissement.
- **Commandes de validation** :
  - `pytest tests/test_reconstruction.py`
  - `pytest tests/test_api_atelier.py`
  - `pytest` (suite complète 159 tests)
  - `npm --prefix frontend test` (Vitest)
  - **E2E réel Mistral** obligatoire (car touche au cœur de `reconstruction.py`) : exécuter `scripts/e2e_j25.py` dans `data_e2e/` et vérifier que la nouvelle version + validation fonctionnent sans corruption.
- **Critères d'acceptation** :
  - Zéro perte de texte après édition directe + réévaluation.
  - Zéro perte de texte après patch partiel (alternative/embellissement) + réévaluation.
  - 100 % des tests pytest et Vitest verts.
  - E2E réel Mistral vert.
- **Handoff session suivante** : Commit `FA1 — Intégrité du ré-ancrage et non-perte de texte`, mise à jour `activeContext.md` (prochain jalon = FA2).

> Créé le 2026-09-09 suite à l'audit approfondi de l'Atelier E5 (jalon F3).
> **RÈGLE@MA�TRESSE : 1 JALON = 1 CONVERSATION DISTINCTE.**
> Ne JAMAIS enchaîner deux jalons dans la même session sans feu vert explicite de l'auteur.
> À cháque début de conversation, lire `activeContext.md` et ce plan.
> Après chaque jalon terminé : tests verts → commit explicite → mise à jour `activeContext.md` + `progress.md` → handoff.
### Jalon FA2 — Identité documentaire, cycle de vie et réévaluation parallèle

- **Objectif** : Éliminer les collisions d'IDs de correction, nettoyer les choix fantômes, uniformiser le cycle de vie après alternative/embellissement et paralléliser la réévaluation.
- **Dépendances** : FA1 terminé.
- **Fichiers à lire obligatoirement** :
  - `memory-bank/activeContext.md`
  - `app/services/atelier.py`
  - `app/services/reconciliation.py`
  - `app/services/reconstruction.py`
  - `tests/test_atelier.py`
  - `tests/test_api_atelier.py`
- **Fichiers à modifier** :
  - `app/services/atelier.py` (`_reevaluer_corrections`, `reevaluer`, `appliquer_alternative`, `choisir_forme`)
  - `app/services/reconstruction.py` (`remplacer_corrections_paragraphe`, gestion des conflits Forme)
  - `tests/test_reconciliation.py`
  - `tests/test_atelier.py`
  - `tests/test_api_atelier.py`
- **Procédure exacte** :
  1. Écrire les tests de régression :
     - Réévaluer `p-1`, puis `p-2` : vérifier que tous les IDs générés dans `document.corrections_barre` sont strictement uniques à l'échelle du document (aucun doublon `c-r0001`).
     - Refuser une correction Forme réévaluée (`choix[c-r...] = "original"`), relancer une réévaluation sur le paragraphe : vérifier que la nouvelle correction ne porte pas un ID recyclé et n'hérite pas d'un refus fantôme.
     - Appliquer une alternative : vérifier que les annotations Style/Technique intersectées ne prétendent plus décrire un fragment qui n'existe plus (politique d'obsolescence explicite).
     - Chevauchement Forme : refuser une Forme prioritaire doit permettre à une Forme concurrente de redevenir applicable (gestion dynamique des conflits).
  2. Implémenter la génération d'identifiants documentaires déterministes et continus :
     - Dans `atelier.py`, inspecter les IDs existants de tout l'état (`c-XXXX`, `c-rXXXX`) et incrémenter un compteur global persistant par document (ex: suite `c-r0001`, `c-r0002`… sans jamais repartir de 1).
     - Dans `reconstruction.remplacer_corrections_paragraphe`, purger explicitement de `etat["choix"]` tous les IDs des corrections supprimées du paragraphe.
  3. Paralléliser `_reevaluer_corrections` :
     - Utiliser `asyncio.gather` comme dans `analyse.py` au lieu de la boucle `for phase in actives` séquentielle.
     - Vérifier que les modèles indispensables sont présents avant lancement (fail-fast cohérent avec l'analyse initiale).
  4. Uniformiser la politique d'obsolescence après alternative manuelle pour Style et Technique.
- **Commandes de validation** :
  - `pytest tests/test_reconciliation.py tests/test_atelier.py tests/test_api_atelier.py`
  - `pytest` (suite complète)
  - `npm --prefix frontend test`
- **Critères d'acceptation** :
  - Unicité absolue des IDs après N réévaluations de paragraphes distincts.
  - Aucun choix résiduel dans `etat["choix"]` pour des corrections qui n'existent plus.
  - Réévaluation exécutée en parallèle pour les phases actives.
- **Handoff session suivante** : Commit `FA2 — Identité documentaire, cycle de vie et réévaluation parallèle`, mise à jour `activeContext.md` (prochain jalon = FA3).


---

### Jalon FA3 — Segmentation atomique aux bornes et document complet (rendu)

- **Objectif** : Corriger le moteur de rendu `rendu.py` pour segmenter le texte exactement aux bornes des annotations (fin du sur-marquage au run entier), supporter le multi-marquage, et envoyer tous les paragraphes au frontend pour que le toggle fonctionne.
- **Dépendances** : FA1 et FA2 terminés.
- **Fichiers à lire obligatoirement** :
  - `memory-bank/activeContext.md`
  - `docs/Architecture application web — v1 (spécification consolidée).md` (§8 rendu, décision 35)
  - `app/services/rendu.py`
  - `app/routes/api.py` (contrat `DocumentAnnote`, `SegmentAnnote`)
  - `tests/test_rendu.py`
- **Fichiers à modifier** :
  - `app/services/rendu.py` (`preparer_document`, `_segments`, `_segments_texte`, gestion des bornes)
  - `app/routes/api.py` (si ajustement de contrat nécessaire avec rétrocompatibilité)
  - `tests/test_rendu.py`
  - `tests/test_api_atelier.py`
- **Procédure exacte** :
  1. Écrire les tests de régression dans `test_rendu.py` :
     - Paragraphe d'un seul run `Alpha beta gamma.` avec correction Style sur `beta` (`[6, 10)`) : vérifier que le segment marqué ne contient QUE `beta`, et que `Alpha ` et ` gamma.` sont des segments neutres distincts.
     - Deux corrections disjointes Style sur `Alpha` et Technique sur `gamma` : vérifier qu'elles ne fusionnent pas en un seul bloc et portent des groupes distincts.
     - Deux corrections chevauchantes sur le même mot (ex. Forme refusée + Style, ou Style + Technique) : vérifier que le segment porte les classes cumulées ET permet d'accéder aux groupes couvrants.
     - Document de 3 paragraphes dont 2 sans correction : vérifier que `preparer_document()` retourne les 3 paragraphes dans `paragraphes`, avec un indicateur clair (ex: `a_corrections: bool`), et que `nb_masques` indique le nombre de paragraphes éligibles au masquage.
  2. Refondre l'algorithme de segmentation dans `app/services/rendu.py` :
     - Collecter l'ensemble des points de découpe : 0, longueur du paragraphe, bornes de chaque run riche `[r.debut, r.fin]`, bornes de chaque Forme acceptée `[c.debut, c.fin]`, et bornes de chaque marque Style/Technique/Refusée `[c.debut, c.fin]`.
     - Trier les points uniques pour créer des intervalles atomiques `[a, b)`.
     - Pour chaque intervalle, déterminer son texte projeté, ses attributs de run (gras, italique, souligné), et la liste ordonnée de toutes les corrections qui le couvrent.
     - Émettre des segments fidèles sans déborder sur le texte adjacent.
  3. Mettre à jour `preparer_document()` : ne plus filtrer les paragraphes sans correction hors de la liste `paragraphes`. Tous les paragraphes sont exposés ; seul le calcul de `nb_masques` est conservé pour informer l'UI.
  4. Mettre à jour les anciens tests de `test_rendu.py` qui affirmaient à tort la disparition des paragraphes propres (incompatibles avec la décision 35).
- **Commandes de validation** :
  - `pytest tests/test_rendu.py`
  - `pytest tests/test_api_atelier.py`
  - `pytest` (suite complète)
- **Critères d'acceptation** :
  - Le marquage Style/Technique ne déborde jamais sur les mots voisins du même run.
  - Les segments multi-marqués préservent l'accès aux corrections concernées.
  - L'API renvoie l'intégralité des paragraphes du texte affiché.
- **Handoff session suivante** : Commit `FA3 — Segmentation atomique aux bornes et document complet`, mise à jour `activeContext.md` (prochain jalon = FA4).

## 1. Contexte et objectif

L'audit senior full-stack / LLM / UI-UX réalisé après le jalon F3 (`023534a`) a mis en évidence que l'architecture « base immuable + annotations » est saine, mais que plusieurs **failles critiques et régressions réelles** menacent l'intégrité des
### Jalon FA4 — Rendu Svelte fidèle, styles réels, formatage Word et robustesse UI

- **Objectif** : Corriger l'affichage dans `DocumentAnnote.svelte`, `Atelier.svelte` et `atelier.css` : restaurer les vraies couleurs des couches, afficher le formatage Word, fiabiliser le toggle, stabiliser les clés Svelte et sécuriser les états asynchrones.
- **Dépendances** : FA3 terminé.
- **Fichiers à lire obligatoirement** :
  - `memory-bank/activeContext.md`
  - `frontend/src/lib/composants/DocumentAnnote.svelte`
  - `frontend/src/lib/styles/atelier.css`
  - `frontend/src/routes/Atelier.svelte`
  - `frontend/src/lib/composants/ToggleMasquer.svelte`
  - `frontend/tests/atelier.test.ts`
- **Fichiers à modifier** :
  - `frontend/src/lib/composants/DocumentAnnote.svelte`
  - `frontend/src/lib/styles/atelier.css`
  - `frontend/src/routes/Atelier.svelte`
  - `frontend/src/lib/composants/ToggleMasquer.svelte`
  - `frontend/tests/atelier.test.ts`
- **Procédure exacte** :
  1. Écrire les tests Vitest correspondants dans `frontend/tests/atelier.test.ts` :
     - Vérifier que le toggle affiche tout le texte par défaut, puis masque les paragraphes sans correction lorsqu'il est coché.
     - Vérifier qu'un texte contenant du gras ou de l'italique rend effectivement `<strong>` ou `<em>` (ou styles équivalents visibles).
     - Vérifier que les boutons de marques portent bien les classes de couleur sans être écrasés par un reset scoped `color: inherit; background: transparent;`.
     - Vérifier qu'un changement d'action (choix Forme) conserve l'onglet actif et ne provoque pas de saut vers `tout`.
     - Vérifier que les clés `{#each}` ne déclenchent pas d'avertissement de doublon lors de segments multiples.
  2. Corriger `DocumentAnnote.svelte` :
     - Remplacer le reset agressif scoped par des règles préservant `var(--corr-forme-texte)`, `var(--corr-forme-fond)`, `var(--corr-technique-fond)`, etc.
     - Rendre le formatage riche : wrapper les fragments avec `<strong>`, `<em>`, `<u>` selon les attributs `gras`, `italique`, `souligne` du segment.
     - Clés de boucle : générer une clé unique déterministe (ex: `p.id + '-' + index + '-' + s.type`).
     - Clavier : exclure les éléments `<del>` non focusables du parcours fléché ou les rendre focusables de façon cohérente sans bloquer le focus.
  3. Corriger `Atelier.svelte` :
     - Le toggle filtre en mémoire `paragraphesAffiches` sur la base de la liste complète désormais reçue de l'API.
     - Préserver l'onglet courant : passer `onglet` dans les payloads d'action ou re-projeter localement sans forcer `tout`.
     - Après chaque mise à jour de l'état, réconcilier `correctionActive` (retrouver la correction par ID ou sélectionner la première active valide).
     - Annuler ou ignorer les requêtes d'onglets périmées (race conditions de clic rapide).
     - Réagir aux changements de prop `analyseId` (navigation directe entre analyses).
     - Corriger la détection de sélection pour ne pas altérer les espaces et tenir compte de l'exclusion des `<del>`.
- **Commandes de validation** :
  - `npm --prefix frontend test`
  - `npm --prefix frontend run check`
  - `npm --prefix frontend run build`
  - `pytest` (vérification de non-régression globale)
- **Critères d'acceptation** :
  - Le toggle permet de basculer instantanément entre texte complet et texte filtré.
  - Le formatage Word et les couleurs des couches apparaissent fidèlement dans le navigateur.
  - Zéro saut d'onglet intempestif après une action de correction.
  - `svelte-check` à 0 erreur et 0 warning.
### Jalon FA5 — Robustesse LLM : Custom Structured Outputs, invariants et prompts

- **Objectif** : Durcir les sorties Mistral, éliminer les risques de troncature silencieuse et de schémas invalides, enrichir la pédagogie des explications (cause → règle → correction → effet) et renforcer l'anti-injection.
- **Dépendances** : FA1 à FA4 terminés.
- **Fichiers à lire obligatoirement** :
  - `memory-bank/activeContext.md`
  - `docs/Architecture application web — v1 (spécification consolidée).md` (§6, §7)
  - `app/llm/prompts.py`
  - `app/llm/client.py`
  - `app/services/analyse.py`
  - `app/services/reconciliation.py`
  - `app/models.py`
  - `tests/test_llm_client.py`
  - `tests/test_reconciliation.py`
- **Fichiers à modifier** :
  - `app/models.py` (`Correction`, validateurs)
  - `app/llm/client.py` (`response_format`, `max_tokens`, gestion `finish_reason`)
  - `app/llm/prompts.py` (consignes Forme/Style/Technique, format d'explication, anti-injection)
  - `app/services/analyse.py`
  - `app/services/reconciliation.py`
  - `tests/test_llm_client.py`
  - `tests/test_reconciliation.py`
- **Procédure exacte** :
  1. Renforcer le modèle Pydantic `Correction` dans `app/models.py` :
     - Invariants stricts : `fin > debut`, `len(original) == (fin - debut)` (ou cohérence validée), interdiction des chaînes vides pour `original`, `explication`, `type`.
     - Supprimer l'obligation pour le LLM d'émettre des IDs ou des phases si Python les réassigne de toute façon, ou créer un schéma d'entrée LLM distinct purifié.
  2. Adapter `ClientLLM` pour Mistral :
     - Passer `response_format={"type": "json_object"}` (ou Custom Structured Output avec JSON Schema si supporté par le modèle configuré).
     - Configurer un `max_tokens` adapté par phase (éviter les coupures à mi-JSON).
     - Lire `finish_reason` : si `"length"`, lever une exception explicite de dépassement de capacité plutôt qu'une erreur de syntaxe JSON générique.
  3. Réviser les prompts dans `app/llm/prompts.py` :
     - Format d'explication pédagogique : structurer `explication` selon le canevas **Cause → Règle/Principe → Correction → Effet**.
     - Forme : interdire explicitement les modifications stylistiques et cibler le fragment minimal.
     - Style : recentrer sur les défauts avérés (répétitions gênantes, pléonasmes) sans écraser la voix d'auteur.
     - Technique : exiger la citation des deux éléments en contradiction dans le texte.
     - Anti-injection : placer la consigne de non-obéissance dans le message système ET dans l'en-tête utilisateur ; balisage clair avec échappement défensif.
  4. Conserver rigoureusement : 3 passes parallèles, Option B intacte, liste vide valide `{"corrections": []}`.
- **Commandes de validation** :
  - `pytest tests/test_llm_client.py tests/test_reconciliation.py tests/test_analyse.py`
  - `pytest` (suite complète)
- **Critères d'acceptation** :
  - Sorties JSON fiables et strictement typées.
  - Explications riches, contextualisées et exploitables par l'auteur.
  - Diagnostic distinct en cas de troncature par tokens.
- **Handoff session suivante** : Commit `FA5 — Robustesse LLM : Custom Structured Outputs, invariants et prompts`, mise à jour `activeContext.md` (prochain jalon = FA6).

### Jalon FA6 — Cohérence transactionnelle, concurrence et alignement d'API

- **Objectif** : Sécuriser les mutations concurrentes de l'état atelier (versioning/révision), unifier les contrats `/api/v1` et éliminer les divergences avec les routes Jinja2 avant leur retrait.
- **Dépendances** : FA1 à FA5 terminés.
- **Fichiers à lire obligatoirement** :
  - `memory-bank/activeContext.md`
  - `app/services/atelier.py`
  - `app/routes/api.py`
  - `app/routes/atelier.py`
  - `tests/test_api_atelier.py`
- **Fichiers à modifier** :
  - `app/services/atelier.py` (gestion de révision / CAS)
  - `app/routes/api.py` (statuts HTTP unifiés, headers ETag/révision)
  - `app/routes/atelier.py` (alignement)
  - `frontend/src/lib/api/atelier.ts`
  - `tests/test_api_atelier.py`
- **Procédure exacte** :
  1. Écrire le test d'intégration pour la concurrence :
     - Deux clients chargent la même analyse terminée.
     - Le premier applique un choix Forme.
     - Le deuxième tente d'appliquer une modification sur un état désynchronisé sans révision : vérifier la détection de conflit ou la résolution cohérente sans écrasement aveugle.
  2. Ajouter une clé de révision (`revision: int` ou hash) dans l'état `documents` :
     - Incrémentée à chaque sauvegarde dans `sauver_etat`.
     - Vérifiée lors des mutations pour garantir qu'un read-modify-write concurrent n'efface pas silencieusement l'action d'un autre onglet.
  3. Aligner les codes HTTP et messages d'erreur entre `/api/v1` et les routes Jinja2 restantes (ex. 400 explicite si analyse non terminée, formats d'erreur JSON systématiques).
- **Commandes de validation** :
  - `pytest tests/test_api_atelier.py`
  - `pytest` (suite complète)
  - `npm --prefix frontend test`
- **Critères d'acceptation** :
  - Aucun écrasement silencieux d'état en cas d'actions concurrentes.
  - Contrats `/api/v1` uniformes et prêts pour le retrait de Jinja2 en F5.
- **Handoff session suivante** : Commit `FA6 — Cohérence transactionnelle, concurrence et alignement d'API`, mise à jour `activeContext.md` (prochain jalon = FA7).

### Jalon FA7 — Restitution pédagogique : diff, sidebar sticky, popovers et clavier

- **Objectif** : Transformer l'expérience de relecture : rendre la barre latérale sticky, connecter visuellement les explications au texte, proposer un popover riche au survol/focus, afficher les diffs avant/après et rendre le clavier fluide.
- **Dépendances** : FA1 à FA6 terminés.
- **Fichiers à lire obligatoirement** :
  - `memory-bank/activeContext.md`
  - `frontend/src/lib/composants/BarreLaterale.svelte`
  - `frontend/src/lib/composants/PopoverSuggestion.svelte`
  - `frontend/src/lib/composants/MenuContextuel.svelte`
  - `frontend/src/routes/Atelier.svelte`
  - `frontend/src/lib/styles/atelier.css`
  - `frontend/src/lib/styles/tokens.css`
- **Fichiers à modifier** :
  - `frontend/src/lib/composants/BarreLaterale.svelte`
  - `frontend/src/lib/composants/PopoverSuggestion.svelte`
  - `frontend/src/lib/composants/MenuContextuel.svelte`
  - `frontend/src/routes/Atelier.svelte`
  - `frontend/src/lib/styles/atelier.css`
  - `frontend/tests/atelier.test.ts`
- **Procédure exacte** :
  1. Rendre la barre latérale sticky et autonome au défilement (`position: sticky; top: 1rem; max-height: calc(100vh - 2rem)`).
  2. Mettre en place la liaison visuelle texte ↔ explication :
     - Clic sur une marque dans le texte : défilement fluide et mise en évidence de la ligne correspondante dans la sidebar.
     - Clic sur une ligne dans la sidebar : défilement centré (`scrollIntoView({ block: "center" })`) et focus sur la marque dans le manuscrit.
  3. Enrichir le détail de la correction :
     - Présentation visuelle claire du diff (Fragment d'origine vs Proposition).
     - Règle mise en exergue (badge/cartouche) distincte de l'explication.
     - Structure Cause / Règle / Correction / Effet.
  4. Popover / info-bulle contextuelle :
     - Afficher un résumé rapide au survol/focus d'une marque sans obliger à quitter le texte des yeux.
     - Accessibilité clavier : ouverture/fermeture par touche Espace/Entrée/Échap.
  5. Menu contextuel et popovers accessibles :
     - Gestion complète du focus (focus initial, piège de focus si modal, restauration du focus à la fermeture).
     - Support tactile : alternative accessible au clic droit pour mobile/tablette.
- **Commandes de validation** :
  - `npm --prefix frontend test`
  - `npm --prefix frontend run check`
  - `npm --prefix frontend run build`
  - `pytest`
- **Critères d'acceptation** :
  - Sidebar sticky utilisable sur de longs chapitres.
  - Navigation bidirectionnelle fluide entre marque et explication.
  - Accessibilité clavier et focus irréprochables.
- **Handoff session suivante** : Commit `FA7 — Restitution pédagogique : diff, sidebar sticky, popovers et clavier`, mise à jour `activeContext.md` (prochain jalon = F4).

---

### Jalons F4 et F5 (Reprise de la roadmap existante)

Après l'achèvement de FA1→FA7, reprendre les jalons tels que spécifiés dans `plan-refonte-frontend.md` :
- **F4 — Finitions UX & identité** : cohérence globale, toasts `aria-live`, responsive complet, microcopy relue, audit formel WCAG AA de tous les contrastes.
- **F5 — Nettoyage & bascule** : suppression de Jinja2/HTMX/Alpine, suppression des routes HTML legacy, E2E Mistral réel ciblant exclusivement `/api/v1`, mise à jour de la spec web v1 consolidée.

---

## 4. Règles d'or pour chaque session

0. **Communication des commits GitHub (OBLIGATOIRE, règle de l'auteur — 2026-09-09)** : à la fin de CHAQUE action, jalon ou session, communiquer EXPLICITEMENT les commits réalisés sur GitHub (hash, intitulé, branche) et confirmer le `git push` effectif. Règle reprise dans `systemPatterns.md` (règle d'architecture n° 9).
1. **Lire obligatoirement en ouverture** : `activeContext.md`, `systemPatterns.md` et la section du jalon dans ce plan.
2. **Ne jamais modifier de code hors du périmètre du jalon en cours.**
3. **Écrire ou adapter les tests de régression avant ou pendant l'implémentation.**
4. **Valider systématiquement** : `pytest` (159+ tests), `npm test` (45+ Vitest), `svelte-check` (0 erreur/warning).
5. **Si l'état (`reconstruction.py`) ou le LLM est modifié** : exécuter l'E2E réel Mistral dans `data_e2e/`.
6. **Avant de fermer la session** :
   - Commit Git explicite avec intitulé du jalon et nombre de tests verts.
   - Mettre à jour `activeContext.md` (statut du jalon, prochain jalon exact).
   - Mettre à jour `progress.md` (tableau des jalons).
   - Cocher le jalon dans ce plan.
   - Laisser l'arbre Git propre (`git status` vide).
