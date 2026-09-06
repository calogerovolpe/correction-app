# Jalons du projet — Journal de bord (À METTRE À JOUR À CHAQUE JALON)

> **Règle obligatoire** : après chaque jalon terminé (code + tests verts + commit + push),
> mettre à jour ce fichier : statut du jalon, contenu livré, décisions prises, prochain jalon.

**Projet** : correction-app — application web de correction de manuscrit
**Stack** : Python 3.11+ / FastAPI / Jinja2 + HTMX + Alpine.js / SQLite (WAL) / Mistral API
**Documents de référence** :
- **Source de vérité unique** : `../../Architecture application web — v1 (spécification consolidée).md`
  (métier + applicatif + état réel ; toute évolution y est répercutée au même jalon) ;
- Historiques (ne pas coder avec) : v3/v4/v5/v6 (fonction OpenWebUI — genèse) et cahier des
  charges initial (remplacé par la spec consolidée).

---

## État d'avancement

| Jalon | Statut | Commit |
|---|---|---|
| J0 — Socle | ✅ Terminé | `4102ada` |
| J1 — Moteur métier | ✅ Terminé | `28f7b62` |
| J2 — MVP de relecture | ✅ Terminé | `aa1d5f9` |
| J2.1 — Correctifs retour utilisateur | ✅ Terminé | `569c784` |
| J3 — Chaîne & codex | ⏳ Prochain | — |
| J4 — Confort | ⬜ À faire | — |
| J5 — Mise en ligne | ⬜ À faire | — |

**État des tests** : 85/85 verts (`pytest`)

---

## J0 — Socle ✅
Squelette FastAPI + Jinja2, schéma SQLite complet (v6 §6.2, renommé sessions→projets),
page d'accueil E1 (création de projets, projet actif), Docker + compose, `.env.example`,
11 tests de schéma (contraintes, CASCADE, trigger RESTRICT projet actif, idempotence).

## J1 — Moteur métier ✅
Cœur v6 sans UI, 100 % testé : `normalisation.py` (§8.1 : CRLF/BOM, paragraphes `\n{2,}` base 1,
offsets tranches Python), `reconciliation.py` (§8.3-8.5 : ancre `contexte_avant`, rejets
individuels, PannePhase = JSON non parsable/racine non conforme — **liste vide jamais une panne**,
déduplication Style prioritaire : recouvrement exact → migration en tooltip, partiel → coexistence),
`chaine.py` (§6.5-6.6 : N+1 conforme / N=N **sans** remplacement → Extrait / N=N avec
remplacement → officiel / refus zéro token), `alertes.py` (§6.7 : numérotation MAX+1 stable,
double barrière /nopb), client LLM compatible OpenAI (ping fail-fast `max_tokens=5`),
mock LLM déterministe. 65 tests.

## J2 — MVP de relecture ✅
E3 (soumission : catégorisation auto, garde-fou `max_caracteres`), jobs asynchrones
(`analyse.py`, statuts en_attente/en_cours/terminee/echec/rejetee, Option B), E4 suivi HTMX
(polling 2 s), E5 résultat annoté (palette WCAG AA v6 §7.2, tooltips multi-cas, pastilles
filtres `aria-pressed`, bouton « Lecture Embellissement », navigation clavier ←/→/Échap,
compteur paragraphes masqués). Phases 3-6 parallèles via Mistral. HTMX/Alpine servis
localement (`app/static/vendor/`), aucun CDN. **E2E réel validé avec Mistral Small** (11
corrections : 7 Forme, 1 Style, 3 Technique). 80 tests.

## J2.1 — Correctifs retour utilisateur ✅
- **Fix critique** : redirection post-soumission pointait toujours vers `/analyses/1`
  (déballage inversé `rowcount` vs `lastrowid`) — régression couverte par test ;
- **Matrice dérogable** (décision de l'auteur) : les cases Forme/Style/Technique/Embellissement
  sont **pré-cochées selon la catégorie** (v6 §5.4 = pré-sélection, plus de rigidité),
  l'utilisateur décoche/coche librement ; champs transmis via un champ caché JSON `phases`
  (FastAPI convertit les valeurs vides en None — piège documenté) ;
- **Jauge de créativité** : slider 0→1.5 lié à la température de l'Embellissement, par analyse ;
- **Analyses récentes** sur l'accueil (10 dernières, statut coloré, cliquables) ;
- **Récupération des jobs orphelins** au démarrage (statut `echec` explicite, jamais de fantôme) ;
- Texte brut : espaces/sauts de ligne conservés et restitués (`white-space: pre-wrap`).
85 tests.

---

## J3 — Chaîne & codex ⏳ (PROCHAIN — spécification détaillée)
Objectif : rendre le système « mémoire » complet. Contenu prévu (cahier des charges §9-J3) :
1. **Écritures narratives** (v6 §6.5, §15) : backup natif `Connection.backup()` AVANT toute
   écriture narrative, puis transaction : chapitres conformes → `chapitres` (texte+hash SHA-256),
   `codex`, `journaux` ; mise à jour `current_chapter_num` + `chain_status='ok'` ;
   `chain_status='rupture'` sur reclassement (métadonnée, sans backup) ;
2. **Phase 2 LLM** : prompt extraction codex (fiches par catégorie v6 §6.2), analyse de cohérence
   (alertes, double barrière déjà prête dans `alertes.py`), relecture-diff du remplacement
   (schéma `DeltaRelecture` déjà prêt dans `models.py`) ;
3. **E2 timeline** : chapitres officiels (Prologue=0, 1..N), numéro attendu suivant en évidence,
   textes reclassés grisés « hors chaîne » ;
4. **E5+** : bandeau d'alertes numérotées (`numero_projet`) + bouton « Choix d'auteur » (= /nopb) ;
5. **RAG alias** (v6 §6.4) : extraction lexicale `\b{terme}\b`, requête `codex_index`,
   collisions d'alias → toutes les fiches candidates au prompt ;
6. **E6 codex éditable** (fiches + alias) et **E7 journaux** (lecture seule) ;
7. **Critère d'acceptation** (scénario réel complet) : Prologue → ch.1 → ch.2 → resoumission
   N=N sans remplacement (→ Extrait, codex intact) → remplacement officiel (relecture-diff,
   codex mis à jour, évolutions historisées) → alerte détectée → « Choix d'auteur » →
   **non re-détectée à la resoumission**.

## J4 — Confort ⬜
E9 (backups liste/restauration/purge, exports md/docx, statistiques, logs debug),
E8 (paramètres + test de connexion), import .docx (italique/gras).

## J5 — Mise en ligne ⬜
Durcissement (auth simple), Caddy (TLS), compose production + volumes, sauvegardes
programmées, doc de déploiement VPS, option Tailscale documentée.
