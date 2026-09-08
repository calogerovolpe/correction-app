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
- **R1 — onglets hybrides + stockage par phase** (rendu/affichage) ;
- **R2 — base immuable + annotations/patches** (état : fin du remappage d'offsets).

Ordre imposé : **R1 avant UX1/UX2** (l'UI se construit sur les onglets) ;
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
| 1 | **R1** | Onglets hybrides (« Tout » + 1 onglet/phase) + stockage PAR PHASE + déduplication devenue règle d'affichage | ⬜ | — |
| 2 | **UX1** | Menu contextuel riche (clic droit sur marque, choix Forme dans le menu) | ⬜ | — |
| 3 | **UX2** | Toggle « masquer les paragraphes sans correction », layout ~1200 px, style des onglets (WCAG AA) | ⬜ | — |
| 4 | **UX3** | Navigation, projets : activation, navbar, suppression (indépendant, intercalable) | ⬜ | — |
| 5 | **R2** | Base immuable + annotations (patches) : refonte `reconstruction.py`, fin du remappage | ⬜ | — |
| 6 | **UX4** | Édition directe sans IA temps réel (« ↻ Re-corriger ») | ⬜ | — |
| 7 | J3 | Chaîne séquentielle & Codex narratif (inchangé) | ⬜ | — |
| 8 | J4 | Confort (backups, exports, stats, paramètres, import .docx) | ⬜ | — |
| 9 | J5 | Mise en ligne (auth, Caddy/TLS, compose prod, doc VPS) | ⬜ | — |
| futur | R3 | Extension des catégories de correction (trivial grâce au modèle) | ⬜ | — |

## Jalon A — Fiabilité du cœur (3 bugs) — ✅ LIVRÉ (commit `b5545f0`)

Historique complet : voir `progress.md`. Contenu : ids de correction uniques
(`reconciliation.renumeroter()`), rejet des no-op Forme, menu contextuel fiable
(CSS `[hidden]`, position fixed, fermeture Échap/clic extérieur).

## Jalon R1 — Onglets hybrides + stockage par phase + déduplication d'affichage

> Objectif : chaque phase isolée sur son onglet ; « Tout » = vue superposée actuelle.
> Zéro token en plus : aucun appel LLM n'est touché (les 3 passes parallèles restent).

1. **Stockage par phase** — `app/services/analyse.py` + `app/models.py` + `app/schema.sql` :
   les corrections sont persistées comme des collections indépendantes PAR PHASE
   (fin du JSON fusionné unique de la table `corrections`). La réassignation
   `renumeroter()` (ids globaux uniques, jalon A) reste appliquée.
2. **Projection par phase** — `app/services/rendu.py` : nouvelle fonction
   `preparer_document_par_phase(phase, ...)` : une seule phase rendue sur le texte
   courant (pas d'empilement, plus de `_couvrants` pour cette projection).
   `preparer_document()` est CONSERVÉE pour l'onglet « Tout ».
3. **Déduplication = règle d'affichage** — `app/services/reconciliation.py` :
   `dedupliquer()` ne migre PLUS l'Embellissement dans le tooltip du Style ; les deux
   coexistent (superposés dans « Tout », séparés dans leurs onglets). La règle
   « Style prioritaire » devient une règle de RENDU.
4. **UI onglets** — `app/templates/analyses/_atelier.html` + `app/static/app.js` +
   `app/static/style.css` : barre d'onglets `Tout | Forme | Style | Technique`
   (onglet « Embellissement » seulement si suggestions) avec `aria-selected` ;
   Alpine passe de `filtres` (booléens cumulables) à `ongletActif` (exclusif) ;
   « Tout » = vue superposée actuelle (les couches CSS restent valables pour cet onglet).
5. **Spec** : mettre à jour `docs/Architecture application web — v1` (§7 rendu,
   §11 décision 29 « couches superposables ») DANS LE MÊME COMMIT que le code.
   Tests : rendu par phase (une correction n'apparaît que dans sa projection),
   rendu « Tout » inchangé (régression), template (onglets rendus, état actif).

## Jalon UX1 — Menu contextuel riche (ex-B)

6. Ouvrir le menu aussi par **clic droit sur une marque** `[data-groupe]` (SANS
   sélection préalable) : reconstruire fragment + paragraphe depuis la correction cliquée.
7. Déplacer « **Appliquer la correction / Garder l'original** » (Forme) dans le menu
   contextuel ; la barre latérale devient lecture seule (explication + règle).
   Alternatives / Embellissement dans le même menu, selon la phase ET l'onglet actif (R1).
   Tests de rendu + tests d'état (`choix` Forme).

## Jalon UX2 — Confort d'affichage (ex-C, amputé des pastilles → devenues onglets en R1)

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

