# Plan — Correctifs atelier E5 & confort UX (multi-sessions, avant J3)

> Créé le 2026-09-09. À relire en début de CHAQUE session, avec toute la memory-bank/.
> Ce plan est LA source de vérité de la série de correctifs : cocher les jalons terminés
> et mettre à jour `activeContext.md` / `progress.md` après chaque session.

## Objectif

Corriger les défauts remontés par l'auteur, JALON PAR JALON, sans régresser.
Chaque jalon : pytest verts → commit « Jx — contenu — N tests verts » → push.
Le jalon suivant repart de l'état committé (donc réalisable sur plusieurs conversations).

## État de départ

- 99/99 tests verts (`pytest`).
- J3 (chaîne séquentielle & codex narratif) est MIS EN ATTENTE jusqu'à la fin des jalons A → E.

## Règles invariables

- Mode Plan d'abord → feu vert de l'auteur avant de coder.
- Tout bug corrigé = un test de régression ; toujours tester le RENDU des templates (pièges : `systemPatterns.md`).
- Ne pas toucher : `.env`, `data/`, `app/static/vendor/`, palette WCAG AA (sauf arbitrage de l'auteur).
- Pas de chunking ; ne pas modifier Option B / fail-fast / « liste vide = jamais une panne ».

## Suivi des jalons

| Jalon | Contenu | Statut | Commit |
|---|---|---|---|
| A | Fiabilité du cœur : ids de correction uniques, no-op rejetés, menu contextuel fiable | ⬜ | — |
| B | Menu contextuel riche (clic droit sur marque, choix Forme dans le menu) | ⬜ | — |
| C | UI/UX atelier : toggle « masqué », layout élargi, pastilles retravaillées | ⬜ | — |
| D | Navigation, projets : activation, navbar, suppression de projet | ⬜ | — |
| E | Édition directe sans IA temps réel (« ↻ Re-corriger ») | ⬜ | — |

## Jalon A — Fiabilité du cœur (3 bugs)

1. **IDs de correction uniques** — `app/services/analyse.py` : après
   `reconciliation.dedupliquer()`, réassigner des `id` GLOBAUX UNIQUES et déterministes.
   - Bug actuel : chaque phase émet ses `id` (ex. `c-0001`) sans coordination ; deux
     corrections de phases différentes peuvent partager le même `id`. `rendu.py`
     construit ses groupes `g-XXXX` par `id` → deux corrections reçoivent le même
     `data-groupe` → la barre latérale affiche une AUTRE correction que celle cliquée,
     et le choix Forme (clé = `id`) colle deux corrections entre elles.
   - Test : deux phases émettant le même `id` → 2 groupes distincts + 2 entrées
     sidebar distinctes + 2 choix Forme indépendants.
2. **Corrections no-op rejetées** — `app/services/reconciliation.py::extraire_corrections` :
   rejeter individuellement toute entrée où `original == correction`
   (ex. « cous » barré pour réécrire « cous », avec explication « aucune correction
   nécessaire »). Test de régression : l'entrée no-op est écartée, les autres restent.
3. **Menu contextuel fiable** — `app/static/app.js` + `style.css` :
   - `.menu-contextuel { display: flex }` neutralise l'attribut `hidden` (règle UA
     `[hidden] { display: none }` surchargée par la classe) → ajouter
     `[hidden] { display: none !important; }` ;
   - menu en `position: fixed` (coordonnées `clientX/clientY`, robuste au scroll) ;
   - positionner le popover de suggestion à l'écran (aujourd'hui hors écran :
     `position:absolute` sans `left/top`) ;
   - fermeture au clic extérieur ET à Échap.
   Test de rendu : menu masqué au chargement, ouvert au clic droit, refermé au clic
   extérieur et après action.

## Jalon B — Menu contextuel riche

4. Ouvrir le menu aussi par **clic droit sur une marque** `[data-groupe]` (SANS
   sélection préalable) : reconstruire fragment + paragraphe depuis la correction cliquée.
5. Déplacer « **Appliquer la correction / Garder l'original** » (Forme) dans le menu
   contextuel ; la barre latérale devient lecture seule (explication + règle).
   Alternatives / Embellissement dans le même menu, selon la phase.
   Tests de rendu + tests d'état (`choix` Forme).

## Jalon C — UI/UX de l'atelier

6. **Affichage du texte** : version ENTIÈRE affichée par défaut + toggle utilisateur
   « Masquer les paragraphes sans correction » (décoché par défaut ; état persisté dans
   `parametres`). `rendu.py` conserve le calcul `nb_masques` (utile au toggle) mais ne
   masque plus par défaut.
   N.B. : ceci RÉVISE la décision 24 du registre (toggle refusé en J2.5) — l'auteur a
   ré-ouvert la décision ; consigné en spec §11 (décision 35) et `projectbrief.md`.
7. **Layout** : élargir l'atelier (~1200 px), barre latérale sticky/scrollable,
   lecture confortable (~65-70 % pour le texte).
8. **Pastilles Forme/Style/Technique** : état actif/inactif clair + compteurs,
   couleurs alignées sur les marquages du texte, WCAG AA.

## Jalon D — Navigation, projets, nettoyage

9. **Activation de projet** : bouton « Activer » par projet
   (`POST /projets/{id}/activer`) → corrige le bug du « 2 » bloqué sur un nouveau
   projet (le 2ᵉ projet restait inactif : E3 lisait l'ancien projet actif et son
   `numero_attendu`).
10. **Barre de navigation globale** plus propre (UI/UX uniquement, AUCUNE route J3 branchée).
11. **Suppression d'un projet** : bouton « Supprimer » + confirmation
    « Voulez-vous effacer … ? » ; suppression TOTALE en cascade (chapitres, codex,
    codex_index, journaux, alertes, analyses, corrections, documents). Projet actif :
    refus protégé (trigger `trg_projet_actif_restrict` existant) avec message
    « Activez d'abord un autre projet ». Tests : cascade + blocage du projet actif.

## Jalon E — Édition directe (décision figée)

12. NE PAS faire d'IA temps réel. Texte éditable dans l'atelier + bouton
    « ↻ Re-corriger » explicite (relance le pipeline sur le texte modifié ; réutilise
    « Soumettre une nouvelle version »). La correction hors-ligne locale (sans token)
    est un candidat J4, à cadrer séparément.

## Après chaque jalon

- pytest verts ;
- mettre à jour `activeContext.md` + `progress.md` (état, avancement) + cocher le jalon ci-dessus ;
- si un contrat métier change, mettre à jour la spec consolidée dans le même commit ;
- commit + push (`Jx — contenu — N tests verts`) ;
- E2E Mistral uniquement si le pipeline LLM est touché (env isolé `data_e2e/`).

## Après le jalon E

Reprendre **J3 — Chaîne séquentielle & Codex narratif** (spécification §9 + critère
d'acceptation : Prologue → ch.1 → ch.2 → resoumission N=N → remplacement officiel →
alerte → non re-détectée).