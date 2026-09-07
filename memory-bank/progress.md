# Progression — jalons, état, décisions

> Dernière mise à jour : 2026-09-07.

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
| J3 — Chaîne séquentielle & Codex narratif | ⏳ **Prochain** | — |
| J4 — Confort | ⬜ À faire | — |
| J5 — Mise en ligne | ⬜ À faire | — |

**Tests : 77/77 verts** (`pytest`). Git : `master` = `origin/master`, HEAD `d5ba4d0` (arbre propre).

## Ce qui marche (validé de bout en bout)

- Soumission d'un texte (Chapitre/Passage/Extrait) avec éditeur Word-fidèle, ping fail-fast, pipeline 4 phases parallèles via Mistral, document annoté E5 (panneau latéral, bulles d'alternatives, filtres, Lecture Embellissement, navigation clavier, compteur de paragraphes masqués), suivi asynchrone HTMX (E4), analyses récentes sur l'accueil, récupération des jobs orphelins.

## Détail des jalons livrés (historique migré de l'ancien journal de bord)

- **J0** : squelette FastAPI + Jinja2, schéma SQLite complet (renommé sessions→projets), page d'accueil E1 (création de projets, projet actif), Docker + compose, `.env.example`, 11 tests de schéma (contraintes, CASCADE, trigger RESTRICT, idempotence).
- **J1** : cœur métier sans UI, 100 % testé — `normalisation.py` (CRLF/BOM, paragraphes base 1, offsets tranches Python), `reconciliation.py` (ancre `contexte_avant`, rejets individuels, PannePhase, liste vide jamais une panne, déduplication Style prioritaire), `chaine.py` (machine N+1, refus zéro token), `alertes.py` (numérotation MAX+1 stable), client LLM + mock.
- **J2** : écran E3 (soumission, matrice de phases, forçage Passage/Extrait, remplacement officiel, garde-fou taille), jobs asynchrones HTMX (E4), phases 3-6 parallèles via Mistral (fail-fast, Option B), document annoté E5 — 80 tests verts + E2E réel Mistral sur un vrai chapitre.
- **J2.1** : fix redirection systématique vers `/analyses/1` (bug `rowcount` vs `lastrowid` — régression couverte par test), cases pré-cochées dérogables (matrice = pré-sélection), jauge de créativité Embellissement, analyses récentes sur l'accueil, récupération des jobs orphelins — 85 tests verts.
- **J2.2** : éditeur Word-fidèle (`texte_riche.py`, runs `RunFormat`, respect des paragraphes), barre latérale droite E5, Style/Embellissement à la demande (bulles popover, `POST /api/alternatives`), Technique latéral, validation finale manuelle (« Soumettre une nouvelle version » / « Valider la version actuelle ») — 89 tests verts.
- **J2.3** : nettoyage strict au collage Word (`o:p`, `&nbsp;`, `<br>`), fin de la détection automatique (catégorie choisie par l'utilisateur), numéro pré-rempli N+1, règle « dernier validé gagne », case opt-in mise à jour Codex/Journaux.
- **J2.4** : rendu E5 réparé (`parser_document_riche`), styles Word restitués dans les segments non corrigés, bulles fiabilisées via `dataset`, nettoyage en profondeur des paragraphes/runs fantômes.

## Reste à faire (priorisé)

1. **J3 — Chaîne & codex** (détail complet dans `activeContext.md`) : écritures narratives (backup + transaction, hash SHA-256), phase 2 LLM (extraction codex, cohérence, relecture-diff), écrans E2/E6/E7 + bandeau d'alertes, RAG alias, fractionnement préalable de `web.py`.
2. **J4 — Confort** : E9 (backups liste/restauration/purge, exports md/docx, statistiques, logs debug), E8 (paramètres + test de connexion), import .docx (italique/gras).
3. **J5 — Mise en ligne** : durcissement (auth simple), Caddy (TLS), compose production + volumes, sauvegardes programmées, doc de déploiement VPS, option Tailscale documentée.
4. **Documentation** : (à valider) transformation du `README.md` du repo en pointeur vers la Memory Bank.

## Problèmes connus

- Aucun bug applicatif ouvert. 77/77 tests verts.
- Documentation : README.md du repo obsolète (bandeau « Jalon courant : J2 ») — correction proposée, en attente de validation.

## Historique des décisions clés

- **A1-A9** (cahier des charges, figés dans la spec consolidée §11) : FastAPI/SQLite/Mistral/Jinja2+HTMX/Alpine, local-first, mono-utilisateur…
- **J2.1** : matrice de phases = pré-sélection dérogable ; jauge de créativité ; analyses récentes ; récupération jobs orphelins.
- **J2.2** : barre latérale à la place des tooltips ; Style/Embellissement à la demande ; validation manuelle des écritures narratives.
- **J2.3** : catégorisation déclarative (fin de la détection auto) ; « dernier validé gagne » sans blocage.
- **Refusés par l'auteur** (ne pas réouvrir) : chunking, échappement backticks, toggle d'affichage du texte complet.
- **2026-09-07** : mise en place de la Memory Bank comme source de vérité unique (option A : fusion du dossier `.clinerules`, journal de bord migré ici).