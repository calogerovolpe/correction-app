# Contexte actif — où nous en sommes MAINTENANT

> Fichier le plus souvent mis à jour. Dernière mise à jour : 2026-09-07.

## Focus du moment

**Préparation du jalon J3 — Chaîne séquentielle & Codex narratif.**

## État global

- Jalon terminé : **J2.4 — Rendu texte riche & fiabilisation bulle d'alternatives** (commit `0bb9577`).
- Dernier commit : `d5ba4d0` (HEAD master = origin/master, arbre propre).
- Tests : **77/77 verts** (`pytest`).
- Application validée de bout en bout avec Mistral Small sur un vrai chapitre (E2E du J2).

## Changements récents

- **J2.4** : rendu E5 réparé (`parser_document_riche` — jamais de JSON brut), styles Word préservés dans les segments non corrigés (`<em>`, `<strong>`, `<u>`), bulles d'alternatives fiabilisées via attributs `data-*`/`dataset`, nettoyage strict des paragraphes et runs fantômes.
- **J2.3** : nettoyage strict au collage Word, catégorisation déclarative (Chapitre/Passage/Extrait au choix), numéro pré-rempli N+1 (ou 0 si vierge), règle « dernier validé gagne » sans blocage, case opt-in mise à jour Codex/Journaux à la validation.
- **Cette session** : mise en place de la Memory Bank (`memory-bank/`) — migration du journal de bord `.clinerules/` (option A : fusion complète, pointeurs à la place).

## Prochaines étapes (ordre)

1. **Commit de la Memory Bank** (message proposé : `Memory Bank — source de vérité unique (migration du journal de bord .clinerules) — 77 tests verts`) + push.
2. (À valider par l'auteur) Transformer le `README.md` du repo en pointeur vers la Memory Bank (son bandeau « Jalon courant : J2 » est obsolète).
3. **J3 — étape 0** : fractionner `app/routes/web.py` (> 300 lignes) en `web.py` (E1 accueil/projets), `analyses.py` (E3 soumission + E4 suivi), `resultat.py` (E5 visualisation/validation/alternatives), `codex.py` (E6/E7 futurs).
4. **J3 — écritures narratives** : backup natif `Connection.backup()` AVANT toute écriture, puis transaction : chapitres conformes → `chapitres` (texte + hash SHA-256), `codex`, `journaux` ; `current_chapter_num` + `chain_status` ('ok' / 'rupture' sans backup).
5. **J3 — phase 2 LLM** : extraction codex (fiches par catégorie), analyse de cohérence (alertes, double barrière `/nopb` prête dans `alertes.py`), relecture-diff du remplacement (`DeltaRelecture` prête dans `models.py`).
6. **J3 — écrans** : E2 timeline (chapitres officiels, numéro attendu, textes reclassés grisés), E5+ bandeau d'alertes + « Choix d'auteur », E6 codex éditable, E7 journaux (lecture seule).
7. **J3 — RAG alias** : extraction lexicale `\b{terme}\b`, requête `codex_index`, collisions d'alias → toutes les fiches candidates au prompt.
8. **J3 — critère d'acceptation** : scénario complet Prologue → ch.1 → ch.2 → resoumission N=N sans remplacement (→ Extrait, codex intact) → remplacement officiel (relecture-diff, codex mis à jour, évolutions historisées) → alerte détectée → « Choix d'auteur » → **non re-détectée à la resoumission**.

## Décisions en cours / à arbitrer

- Aucune décision métier en attente. Décisions figées : `projectbrief.md` ; historique : `progress.md`.

## Dettes / anomalies connues (documentation)

- `README.md` du repo : bandeau obsolète (« Jalon courant : J2 ») — transformation en pointeur à valider.
- Ancien `.clinerules/03-commandes-et-tests.md` indiquait « 85 verts attendus » : chiffre erroné, le réel est **77** après réorganisation des tests (J2.3/J2.4). Corrigé dans `techContext.md`.