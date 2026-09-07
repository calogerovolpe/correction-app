# Contexte actif — où nous en sommes MAINTENANT

> Fichier le plus souvent mis à jour. Dernière mise à jour : 2026-09-07 (jalon J2.5 livré).

## Focus du moment

**Préparation du jalon J3 — Chaîne séquentielle & Codex narratif** (l'atelier v2, jalon correctif J2.5, est livré).

## État global

- Jalon terminé : **J2.5 — Atelier v2 : texte courant, couches superposables, embellissement/alternatives par clic droit, validation du texte affiché**.
- Tests : **99/99 verts** (`pytest`).
- **E2E réel Mistral OK** de bout en bout (`scripts/e2e_j25.py`, environnement isolé `data_e2e/`) : analyse 3 phases → nouvelle version (texte courant repris) → validation (chapitre officiel corrigé, hash, chaîne N+1, backup natif créé).
- Application validée de bout en bout avec Mistral Small.

## Changements récents (J2.5)

- **Bugs bloquants réparés** (hérités de J2.2/J2.3, invisibles aux tests précédents) :
  - « Soumettre une nouvelle version » était un **squelette non implémenté** (boucle `pass`) + déballage `rowcount`/`lastrowid` → redirection systématique `/analyses/1` (régression du piège J2.1) ;
  - le bouton « Valider la version actuelle » **ne s'affichait plus** (décisions J2.3 `chapitre/passage/extrait` vs tests `conforme/remplacement_officiel`) ;
  - la validation enregistrait le texte ORIGINAL au lieu de la version choisie.
- **Atelier v2** : état courant matérialisé (nouvelle table `documents`, nouveau service pur `reconstruction.py`) ; rendu en **couches superposables** (`rendu.py` réécrit — Technique désormais aussi dans le corps du texte, fond jaune) ; **sélection + clic droit** → « Embellir la sélection » (réévaluation du paragraphe via LLM) et « Trouver une alternative » (synonyme/champ lexical) ; bouton « ↻ Réévaluer » sur les paragraphes modifiés ; validation = texte affiché + **backup natif SQLite** + rotation ; « Soumettre un autre texte » avec E3 pré-cochée (mémoire des configurations dans `parametres`) ; corrections Forme appliquées par défaut, refusables ; branches mortes (`decision == 'conforme'…`, bandeau `reclassement_extrait`, tooltips `_cas.html`) supprimées ; navigation clavier réellement branchée (`app.js` réécrit, était mort) ; matrice E3 ramenée à 3 phases (jauge supprimée) ; fractionnement de fait : `web.py` (E1/E3/E4, ~230 lignes) + `atelier.py` (E5 + workflow, ~400 lignes).
- **Divers** : config/docstrings alignées sur « Mistral uniquement » ; README transformé en pointeur Memory Bank ; `Ouvrir Correction.bat` committé ; spec §5.3/§6.1/§8.2/§10/§11 (décisions 27-32) mise à jour dans le même commit.

## Prochaines étapes (ordre) — J3

1. **Écritures narratives complètes** : backup (déjà en place à la validation) + transaction : `codex` (fiches par catégorie), `journaux` (écriture/évolution) ; case opt-in `avec_codex` désormais câblée.
2. **Phase 2 LLM** : extraction codex, analyse de cohérence (alertes, double barrière prête dans `alertes.py`), relecture-diff du remplacement (`DeltaRelecture` prête).
3. **Écrans** : E2 timeline, E5 bandeau d'alertes + « Choix d'auteur », E6 codex éditable, E7 journaux (lecture seule).
4. **RAG alias** : extraction lexicale, `codex_index`, collisions → fiches candidates au prompt.
5. **Critère d'acceptation J3** : scénario complet Prologue → ch.1 → ch.2 → resoumission N=N sans remplacement → remplacement officiel (relecture-diff) → alerte → « Choix d'auteur » → non re-détectée.

## Décisions en cours / à arbitrer

- Aucune décision métier en attente. Décisions figées : `projectbrief.md` (+ spec §11 décisions 27-32) ; historique : `progress.md`.

## Dettes / anomalies connues (documentation)

- `app/routes/atelier.py` (~400 lignes) > cible 300 : le fractionnement fin (par écran) reste planifié pendant J3 si le fichier grossit encore (règle systemPatterns n° 8).
- Le déballage `(lastrowid, rowcount)` est documenté comme piège — un commentaire de garde figure sur le seul site restant (`nouvelle-version`).