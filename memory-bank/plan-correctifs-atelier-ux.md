# Plan — Refonte du rendu (onglets/projections) + correctifs UX → J3 (roadmap maîtresse)

> Créé le 2026-09-09 (réorganisé le même jour après arbitrage « refonte rendu/état »).
> À relire en début de CHAQUE session, avec toute la memory-bank/.
> Ce plan est LA source de vérité de la série R1/UX1→UX4 : cocher les jalons terminés
> et mettre à jour `activeContext.md` / `progress.md` après chaque session.

## Objectif

Corriger les défauts remontés par l'auteur ET poser la refonte architecturale du
rendu/état (onglets par phase, base immuable + annotations), JALON PAR JALON,
sans régresser. Chaque jalon : pytest verts → commit « Jx — contenu — N tests verts »
→ push. Le jalon suivant repart de l'état committé (multi-sessions).

## État de départ

- 108/108 tests verts (`pytest`) — 99 à l'origine de la série + 9 tests de régression du jalon A.
- J3 (chaîne séquentielle & codex narratif) est MIS EN ATTENTE jusqu'à la fin des jalons A → UX4.

## Règles invariables

- Mode Plan d'abord → feu vert de l'auteur avant de coder.
- Tout bug corrigé = un test de régression ; toujours tester le RENDU des templates (pièges : `systemPatterns.md`).
- Ne pas toucher : `.env`, `data/`, `app/static/vendor/`, palette WCAG AA (sauf arbitrage de l'auteur).
- Pas de chunking ; ne pas modifier Option B / fail-fast / « liste vide = jamais une panne ».
- Les onglets ne changent RIEN aux appels LLM (3 passes parallèles conservées, zéro token en plus).

## Architecture cible (décisions de l'auteur, 2026-09-09)

```
1. TEXTE SOURCE (normalisé)         ← base immuable (spec §4.1, déjà posée)
2. Chaque phase = UNE COLLECTION de corrections indépendante (stockage par phase)
3. « Texte courant » = PROJECTION : les Forme ACCEPTÉES appliquées (filtre) ;
   refuser = retirer du filtre ; Style/Technique = marquage, jamais réécriture
4. Rendu = PROJECTIONS PAR PHASE (onglets) + projection « Tout » (superposition)
5. Déduplication = règle d'AFFICHAGE, plus jamais une mutation de données
```

Deux refontes :
- **R1 — onglets hybrides + stockage par phase** (rendu/affichage), DÉCOUPÉE en deux conversations : **R1-a** (UI + projection par phase, rendu seul) puis **R1-b** (stockage par phase + fin de `CorrectionFusionnee`) ;
- **R2 — base immuable + annotations/patches** (état : fin du remappage d'offsets).

Ordre imposé : **R1-a → R1-b avant UX1/UX2** (l'UI se construit sur les onglets) ;
**R2 avant UX4 et J3** (édition directe et validation officielle lisent l'état) ;
**UX3 est indépendant** (intercalable à tout moment).

## Correspondance avec l'ancien plan (B/C/D/E)

| Ancien jalon | Devient | Changement |
|---|---|---|
| B — Menu contextuel riche | **UX1** | inchangé, mais se construit sur l'UI à onglets (après R1) |
| C — UI/UX (toggle, layout, pastilles) | **UX2** | les « pastilles » deviennent les ONGLETS de R1 ; restent ici toggle/layout/style |
| D — Navigation, projets | **UX3** | inchangé ; indépendant (intercalable) |
| E — Édition directe sans IA | **UX4** | DÉPLACÉ APRÈS R2 : repose sur le nouveau modèle d'état |

## Suivi des jalons

| Ordre | Jalon | Contenu | Statut | Commit |
|---|---|---|---|---|
| ✅ | A | Fiabilité du cœur : ids uniques, no-op rejetés, menu contextuel fiable | ✅ | `b5545f0` |
| 1 | **R1-a** | Onglets UI + projection par phase (rendu SEUL — stockage et `dedupliquer` inchangés) | ✅ | `245071b` |
| 2 | **R1-b** | Stockage PAR PHASE + déduplication devenue règle d'affichage + fin de `CorrectionFusionnee` | ✅ | `c911547` |
| 3 | **UX1** | Menu contextuel riche (clic droit sur marque, choix Forme dans le menu) | ⬜ | — |
| 4 | **UX2** | Toggle « masquer les paragraphes sans correction », layout ~1200 px, style des onglets (WCAG AA) | ⬜ | — |
| 5 | **UX3** | Navigation, projets : activation, navbar, suppression (indépendant, intercalable) | ⬜ | — |
| 6 | **R2** | Base immuable + annotations (patches) : refonte `reconstruction.py`, fin du remappage | ⬜ | — |
| 7 | **UX4** | Édition directe sans IA temps réel (« ↻ Re-corriger ») | ⬜ | — |
| 8 | J3 | Chaîne séquentielle & Codex narratif (inchangé) | ⬜ | — |
| 9 | J4 | Confort (backups, exports, stats, paramètres, import .docx) | ⬜ | — |
| 10 | J5 | Mise en ligne (auth, Caddy/TLS, compose prod, doc VPS) | ⬜ | — |
| futur | R3 | Extension des catégories de correction (trivial grâce au modèle) | ⬜ | — |

## Jalon A — Fiabilité du cœur (3 bugs) — ✅ LIVRÉ (commit `b5545f0`)

Historique complet : voir `progress.md`. Contenu : ids de correction uniques
(`reconciliation.renumeroter()`), rejet des no-op Forme, menu contextuel fiable
(CSS `[hidden]`, position fixed, fermeture Échap/clic extérieur).

## Jalon R1-a — Onglets UI + projection par phase (rendu SEUL, stockage inchangé)

> Objectif : chaque phase isolée sur son onglet ; « Tout » = vue superposée actuelle.
> Zéro token : aucun appel LLM n'est touché (les 3 passes parallèles restent).
> ⚠️ CONVERSATION 1 sur 2 : le stockage et `dedupliquer()` ne sont PAS touchés ici (R1-b).

1. **Projection par phase** — `app/services/rendu.py` : ajouter
   `preparer_document_par_phase(paragraphes, entrees, phase, choix, modifies=None)` :
   filtrer `entrees` sur `e["fusion"].correction.phase == phase` puis appeler la
   `preparer_document()` existante (AUCUNE duplication de la logique de segments).
   `preparer_document()` reste la projection « Tout ».
2. **Routage de l'onglet** — `app/routes/atelier.py` :
   - `_contexte_resultat(analyse, etat, erreur=None, onglet="tout")` : si
     `onglet != "tout"` → `preparer_document_par_phase`, sinon `preparer_document` ;
   - GET `page_analyse` : lire `onglet` dans la query string ;
   - POST (`choix-forme`, `reevaluer`, `appliquer-alternative`,
     `appliquer-embellissement`) : lire un champ `onglet: str = Form("tout")` et le
     transmettre à `_rendre_atelier` — on reste sur l'onglet après l'action.
3. **UI onglets** — `app/templates/analyses/_atelier.html` : remplacer la
   `<div class="legende">` (3 pastilles) par une barre d'onglets
   `Tout | Forme | Style | Technique` (+ onglet `Embellissement` SEULEMENT si une
   correction `embellissement` existe dans `document.corrections_barre`) ;
   boutons `data-action="onglet" data-onglet="..."`, état actif `aria-selected` ;
   ajouter un champ caché `onglet` dans chaque formulaire de l'atelier.
4. **JS + CSS** — `app/static/app.js` : clic onglet → `poster('/analyses/{id}/onglet',
   {onglet})` (NOUVELLE route POST qui re-rend `_atelier.html`) ; retirer la logique
   Alpine `filtres` (booléens cumulables). `app/static/style.css` : style des onglets
   (palette WCAG AA existante) ; supprimer les règles `.filtre-*-off` devenues
   orphelines (vérifier tout autre usage avant).
5. **NE PAS toucher** : le stockage (`analyse.py` écriture de `corrections`,
   `schema.sql`, `_charger_fusion`), `dedupliquer()`, `CorrectionFusionnee`,
   `embellissement_migre`, `EmbellissementMigre` — tout cela est R1-b.
6. **Spec + tests** : mettre à jour `docs/Architecture application web — v1`
   (§7 rendu, §11 décision 29 « couches superposables » → « onglets hybrides »)
   DANS LE MÊME COMMIT. Tests : `test_rendu.py` (une correction n'apparaît que dans
   sa projection ; « Tout » inchangé — régression), test de template (barre
   d'onglets rendue, `aria-selected`, `?onglet=forme` rend la projection Forme),
   test de route (après `POST choix-forme` avec `onglet=forme`, on reste sur Forme).
   Finition : pytest 100 % verts → commit `R1-a — onglets hybrides + projection
   par phase — N tests verts` → push → MAJ `activeContext.md`/`progress.md`.

### ⚠️ État du code À LA FIN de R1-a (handoff OBLIGATOIRE pour R1-b)

> ✅ **CONSOMMÉ** — R1-b est livré (`c911547`, voir « Suivi des jalons ») ; section conservée pour l'historique.

- Stockage TOUJOURS : liste plate de `CorrectionFusionnee` dans
  `corrections.data_json` (un JSON par analyse) — RIEN n'a changé côté stockage.
- `dedupliquer()` migre TOUJOURS l'Embellissement dans le Style (code MORT :
  aucune correction `embellissement` n'est produite par le pipeline — l'embellissement
  est à la demande) — inoffensif, laissé tel quel volontairement.
- La barre d'onglets est en place ; `onglet` circule via query string (GET) et
  champ de formulaire (POST) ; nouvelle route POST `/analyses/{id}/onglet`.
- `preparer_document` (Tout) et `preparer_document_par_phase` coexistent dans
  `rendu.py` (la seconde filtre les `entrees` avant d'appeler la première).
- `CorrectionFusionnee` / `embellissement_migre` / `EmbellissementMigre` existent
  encore (modèles et usages intacts).
- ❌ NE PAS « corriger » cet état intermédiaire avant R1-b : il est volontaire.

## Jalon R1-b — Stockage par phase + déduplication d'affichage (fin de `CorrectionFusionnee`)

> Prérequis : R1-a committé et vert (lire « État du code À LA FIN de R1-a » ci-dessus).
> ⚠️ CONVERSATION 2 sur 2. NE touche PAS à l'UI (les onglets de R1-a restent)
> ni au pipeline LLM (3 phases parallèles, Option B, fail-fast inchangés).

1. **Modèles** — `app/models.py` : supprimer `EmbellissementMigre` et
   `CorrectionFusionnee` (les services/rendu travaillent sur `Correction` direct).
2. **Réconciliation** — `app/services/reconciliation.py` :
   - `dedupliquer()` : supprimer la branche de migration Style/Embellissement — en
     cas de recouvrement exact, les DEUX corrections coexistent (superposées dans
     « Tout », séparées dans leurs onglets) ; si la fonction ne fait plus rien, la
     supprimer (décision à consigner dans le commit) ;
   - `renumeroter()` : signature `list[Correction]` → `list[Correction]`
     (ids globaux uniques et déterministes conservés — jalon A, décision 33).
3. **Stockage par phase** — `app/services/analyse.py` : après `renumeroter`, écrire
   `corrections.data_json` comme un dict par phase
   `{"forme": [...], "style": [...], "technique": [...]}` (valeurs =
   `Correction.model_dump()`). AUCUN changement de colonne dans `schema.sql`
   (toujours `data_json` texte) — documenter le format dans la spec (§3, §8).
4. **Lecture + état** — `app/routes/atelier.py` : `_charger_fusion` lit le dict par
   phase et l'aplatit en `list[Correction]` (renommée `_charger_corrections`) ;
   `_reevaluer_corrections` produit des `Correction` (plus de `CorrectionFusionnee`).
   `app/services/reconstruction.py` : `etat_initial(list[Correction], ...)` ;
   renommage MÉCANIQUE ET COMPLET `entree["fusion"]` → `entree["correction"]`
   (y compris `_maj_correction` et le round-trip `vers_json`/`depuis_json`).
   `app/services/rendu.py` : mêmes accès renommés (`_info`, `_classe_marque`,
   `_segments`, `_couvrants`, `_segments_texte`, `_segment_forme`).
5. **NE PAS toucher** : l'UI (template, CSS, JS), le pipeline LLM, les règles
   Option B / fail-fast / « liste vide = jamais une panne ».
6. **Tests** — `test_reconciliation.py` : remplacer les tests de migration
   (`test_recouvrement_exact_style_prioritaire_embellissement_migre`,
   `test_renumeroter_conserve_l_embellissement_migre`) par des tests de la NOUVELLE
   règle (recouvrement exact Style/Embellissement → les DEUX coexistent, aucune
   absorbée) et de `renumeroter` sur `list[Correction]` ; `test_llm_client.py`
   (flux complet sans `embellissement_migre`) ; `test_reconstruction.py`
   (`test_aller_retour_json_est_fidele` sur le nouveau format) ; `test_rendu.py`,
   `test_atelier.py` (fixtures en `Correction`).
   ⚠️ RISQUE PRINCIPAL : le renommage `entree["fusion"]` → `entree["correction"]`
   doit être COMPLET — grep `fusion` dans `app/` après l'opération, la suite entière
   doit rester verte.
   Finition : pytest 100 % verts → commit `R1-b — stockage par phase + déduplication
   affichage (fin CorrectionFusionnee) — N tests verts` → push → spec (§3, §8.4,
   §11 décision 29) dans le même commit → MAJ `activeContext.md`/`progress.md`
   → prochain jalon = UX1.

### État du code À LA FIN de R1-b (cible)

- `corrections.data_json` = dict par phase ; `CorrectionFusionnee`,
  `embellissement_migre`, `EmbellissementMigre` SUPPRIMÉS ;
  `reconstruction`/`rendu`/`atelier` travaillent sur `Correction` direct ;
  déduplication = règle d'affichage ; UI (onglets R1-a) inchangée.
- Prêt pour **UX1** (menu contextuel riche).


## Jalon UX1 — Menu contextuel riche (ex-B)

6. Ouvrir le menu aussi par **clic droit sur une marque** `[data-groupe]` (SANS
   sélection préalable) : reconstruire fragment + paragraphe depuis la correction cliquée.
7. Déplacer « **Appliquer la correction / Garder l'original** » (Forme) dans le menu
   contextuel ; la barre latérale devient lecture seule (explication + règle).
   Alternatives / Embellissement dans le même menu, selon la phase ET l'onglet actif (R1).
   Tests de rendu + tests d'état (`choix` Forme).

## Jalon UX2 — Confort d'affichage (ex-C, amputé des pastilles → devenues onglets en R1-a)

8. **Affichage du texte** : version ENTIÈRE affichée par défaut + toggle utilisateur
   « Masquer les paragraphes sans correction » (décoché par défaut ; état persisté
   dans `parametres`). `rendu.py` conserve le calcul `nb_masques` mais ne masque plus
   par défaut. (RÉVISE la décision 24 — déjà acté, décision 35.)
9. **Layout** : élargir l'atelier (~1200 px), barre latérale sticky/scrollable,
   lecture confortable (~65-70 % pour le texte).
10. **Style des onglets R1** : états actif/inactif clairs + compteurs par onglet,
    couleurs alignées sur les marquages du texte, WCAG AA.

## Jalon UX3 — Navigation, projets, nettoyage (ex-D) — INDÉPENDANT, intercalable

11. **Activation de projet** : bouton « Activer » par projet
    (`POST /projets/{id}/activer`) → corrige le bug du « 2 » bloqué sur un nouveau
    projet (E3 lisait l'ancien projet actif et son `numero_attendu`).
12. **Barre de navigation globale** plus propre (UI/UX uniquement, AUCUNE route J3 branchée).
13. **Suppression d'un projet** : bouton « Supprimer » + confirmation ; suppression
    TOTALE en cascade (chapitres, codex, codex_index, journaux, alertes, analyses,
    corrections, documents). Projet actif : refus protégé
    (trigger `trg_projet_actif_restrict`) — « Activez d'abord un autre projet ».
    Tests : cascade + blocage du projet actif.

## Jalon R2 — Base immuable + annotations (patches)

> Le plus gros levier de propreté : fin du « texte mutable + remappage d'offsets ».
> Fichier central et très testé : à faire derrière le filet des tests + tests de rendu.

14. **Modèle d'état cible** — `app/services/reconstruction.py` + `app/routes/atelier.py` :
    - l'état courant ne stocke PLUS un texte réécrit avec offsets remappés, mais la
      base immuable (texte normalisé) + les corrections en coordonnées de la BASE +
      les filtres (Forme acceptées/refusées) + les modifications manuelles (patches) ;
    - « texte courant » = PROJECTION calculée (appliquer les patches acceptés, triés) ;
      refuser une Forme = retirer du filtre (aucun remappage) ;
    - Style/Technique = marquage sur la base, jamais de réécriture ;
    - les corrections ne sont plus jamais « décalées » : elles portent leurs offsets
      d'origine ; les modifications manuelles sont des patches indépendants.
15. **Migration** : nouvelle représentation JSON de la table `documents` — adaptateur
    de lecture acceptant l'ancien format, ou re-parsing depuis `analyses.texte_source`
    + `corrections.data_json` (arbitrer au moment du jalon).
16. **Workflow inchangé vu de l'UI** : choix Forme, réévaluation paragraphe,
    embellissement, « Valider » = texte affiché (projection) + hash + backup.
    Tests : `test_reconstruction.py` réécrit/adapté ; 100 % verts ; E2E Mistral
    (le pipeline LLM n'est pas touché mais l'état oui → E2E requis).

## Jalon UX4 — Édition directe sans IA temps réel (ex-E)

17. NE PAS faire d'IA temps réel. Texte éditable dans l'atelier + bouton
    « ↻ Re-corriger » explicite (relance le pipeline sur le texte modifié ; réutilise
    « Soumettre une nouvelle version »). Dépend de R2 : une édition = un patch
    indépendant, pas un splice + remappage. La correction hors-ligne locale (sans
    token) reste un candidat J4, à cadrer séparément.

## Jalon R3 — Extension des catégories (futur, cadré à la demande)

18. Ajouter une catégorie de correction = une config de phase (modèle + consigne +
    température) + un onglet + une projection. ZÉRO changement au cœur
    (`reconstruction`/`rendu`). C'est la justification du modèle
    annotations/projections.

## Après chaque jalon

- pytest verts ;
- mettre à jour `activeContext.md` + `progress.md` (état, avancement) + cocher le jalon ci-dessus ;
- si un contrat métier change, mettre à jour la spec consolidée dans le même commit ;
- commit + push (`Jx — contenu — N tests verts`) ;
- E2E Mistral si le pipeline LLM OU l'état (`reconstruction`) est touché (env isolé `data_e2e/`).

## Après le jalon UX4

Reprendre **J3 — Chaîne séquentielle & Codex narratif** (spécification §9 + critère
d'acceptation : Prologue → ch.1 → ch.2 → resoumission N=N → remplacement officiel →
alerte → non re-détectée), puis J4, puis J5.

