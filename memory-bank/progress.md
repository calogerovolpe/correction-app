# Progression — jalons, état, décisions

> Dernière mise à jour : 2026-09-09 (série de correctifs UX engagée — J3 en attente).

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
| **Correctifs atelier & confort UX (A→E, multi-sessions)** | ⏳ **En cours (avant J3)** | — |
| J3 — Chaîne séquentielle & Codex narratif | ⬜ En attente (après correctifs) | — |
| J4 — Confort | ⬜ À faire | — |
| J5 — Mise en ligne | ⬜ À faire | — |

**Tests : 99/99 verts** (`pytest`). E2E réel : `scripts/e2e_j25.py` (isolé dans `data_e2e/`).

## Ce qui marche (validé de bout en bout)

- Soumission d'un texte (Chapitre/Passage/Extrait) avec éditeur Word-fidèle, ping fail-fast, pipeline 3 phases parallèles via Mistral, suivi asynchrone HTMX (E4), analyses récentes sur l'accueil, récupération des jobs orphelins.
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

## Reste à faire (priorisé)

1. **Correctifs atelier & confort UX** (jalons A → E, multi-sessions — roadmap : `plan-correctifs-atelier-ux.md`) : fiabilité du cœur (ids uniques, no-op, menu contextuel), menu contextuel riche, UI/UX atelier (toggle masqué, layout, pastilles), navigation/projets (activation, navbar, suppression de projet), édition directe sans IA temps réel.
2. **J3 — Chaîne & codex** (EN ATTENTE, détail dans `activeContext.md`) : écritures narratives (transaction, `avec_codex` câblé, codex/journaux), phase 2 LLM (extraction codex, cohérence, relecture-diff), écrans E2/E6/E7 + bandeau d'alertes, RAG alias.
3. **J4 — Confort** : E9 (backups liste/restauration/purge, exports md/docx, statistiques, logs debug), E8 (paramètres + test de connexion), import .docx (italique/gras).
4. **J5 — Mise en ligne** : durcissement (auth simple), Caddy (TLS), compose production + volumes, sauvegardes programmées, doc de déploiement VPS, option Tailscale documentée.

## Problèmes connus

- 99/99 tests verts ; E2E réel Mistral OK.
- **Bugs constatés par l'auteur (correctifs en cours — roadmap `plan-correctifs-atelier-ux.md`)** : barre latérale désynchronisée (ids de correction non uniques entre phases) ; corrections no-op (« cous » → « cous ») ; menu contextuel non fiable (`hidden` neutralisé par le CSS, popover hors écran) ; pas de menu contextuel sur une marque ; numéro attendu erroné pour un nouveau projet (projet non activable).
- Dette : `atelier.py` ~400 lignes — fractionnement fin planifié pendant J3 si croissance (règle 300 lignes).

## Historique des décisions clés

- **A1-A9** (cahier des charges, figés dans la spec consolidée §11) : FastAPI/SQLite/Mistral/Jinja2+HTMX/Alpine, local-first, mono-utilisateur…
- **J2.1** : matrice de phases = pré-sélection dérogable ; jauge de créativité ; analyses récentes ; récupération jobs orphelins.
- **J2.2** : barre latérale à la place des tooltips ; Style/Embellissement à la demande ; validation manuelle des écritures narratives.
- **J2.3** : catégorisation déclarative (fin de la détection auto) ; « dernier validé gagne » sans blocage.
- **J2.5 (arbitrages de l'auteur, révisent J2.1/J2.2)** : validation du texte AFFICHÉ (chapitres, confirmation) ; Embellissement à la demande (fin de la jauge à la soumission) ; alternatives par sélection + clic droit (fin des bulles au clic gauche) ; couches superposables (Technique fond jaune dans le texte) ; « Soumettre un autre texte » avec configurations mémorisées ; backup natif à la validation. Détail : spec §11 décisions 27-32.
- **Refusés par l'auteur** (ne pas réouvrir) : chunking, échappement backticks, toggle d'affichage du texte complet.
- **2026-09-07** : Memory Bank source de vérité unique ; **J2.5** atelier v2.
- **2026-09-09** : série de correctifs atelier & confort UX arbitrée (roadmap `plan-correctifs-atelier-ux.md` ; spec §11 décisions 33-38 ; révise la décision 24) ; J3 mis en attente.