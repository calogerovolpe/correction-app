# Contexte actif — où nous en sommes MAINTENANT

> Fichier le plus souvent mis à jour. Dernière mise à jour : 2026-09-09 (jalon A livré — série de correctifs en cours, J3 en attente).

## Focus du moment

**Série de correctifs atelier E5 & confort UX (multi-sessions) — AVANT J3.**
La roadmap détaillée, jalon par jalon, est dans **`plan-correctifs-atelier-ux.md`** (même dossier) : la RELIRE EN DÉBUT DE SESSION. Jalons B → E restants, un commit par jalon ; le suivi (statut/commit) est tenu à jour dans ce fichier.

## État global

- Jalons terminés : **J2.5 — Atelier v2** puis **A — Fiabilité du cœur (ids uniques, no-op, menu contextuel)**.
- Tests : **108/108 verts** (`pytest`).
- **E2E réel Mistral OK** de bout en bout (`scripts/e2e_j25.py`, environnement isolé `data_e2e/`) : analyse 3 phases → nouvelle version (texte courant repris) → validation (chapitre officiel corrigé, hash, chaîne N+1, backup natif créé).
- Application validée de bout en bout avec Mistral Small.

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

1. **Correctifs atelier & confort UX** (jalons B → E, multi-sessions — A ✅ livré) : voir `plan-correctifs-atelier-ux.md` — menu contextuel riche (clic droit sur marque SANS sélection, choix Forme déplacé dans le menu), UI/UX (toggle « masquer » — révise la décision 24, layout élargi ~1200 px, pastilles retravaillées), navigation/projets (activation — bug du « 2 » bloqué, navbar, suppression de projet avec confirmation + protection du projet actif), édition directe sans IA temps réel (« ↻ Re-corriger »).
2. **J3 — Chaîne & codex** (EN ATTENTE) : écritures narratives (transaction, `avec_codex` câblé, codex/journaux), phase 2 LLM (extraction codex, cohérence, relecture-diff), écrans E2/E6/E7 + bandeau d'alertes, RAG alias. Critère d'acceptation : Prologue → ch.1 → ch.2 → resoumission N=N sans remplacement → remplacement officiel (relecture-diff) → alerte → « Choix d'auteur » → non re-détectée.

## Décisions en cours / à arbitrer

- Nouvelles décisions arbitrées (2026-09-09) : spec §11 **décisions 33-38** (ids de correction uniques, rejet des no-op, toggle « masquer » — **RÉVISE la décision 24**, menu contextuel riche, suppression de projet, édition sans IA temps réel) — voir `plan-correctifs-atelier-ux.md`.
- Précision d'implémentation du jalon A (décision 34) : le rejet des no-op ne concerne que la **phase Forme** — Style/Technique marquent SANS réécrire (`original == correction` y est le mode de marquage légitime, ex. fond jaune Technique).
- Décisions antérieures figées : `projectbrief.md` (+ spec §11 décisions 1-32) ; historique : `progress.md`.

## Dettes / anomalies connues (documentation)

- **Limite connue (jalon A, hors des 3 bugs)** : `_reevaluer_corrections` (`atelier.py`) régénère des ids `c-r0001…` avec un compteur remis à zéro à CHAQUE appel — deux réévaluations de paragraphes DIFFÉRENTS dans la même session peuvent théoriquement produire le même id (même classe de collision que le bug 1). Cas rare, non constaté ; à traiter si l'atelier le révèle (piste : continuer la séquence `c-r` à l'échelle du document).
- `app/routes/atelier.py` (~400 lignes) > cible 300 : le fractionnement fin (par écran) reste planifié pendant J3 si le fichier grossit encore (règle systemPatterns n° 8).
- Le déballage `(lastrowid, rowcount)` est documenté comme piège — un commentaire de garde figure sur le seul site restant (`nouvelle-version`).