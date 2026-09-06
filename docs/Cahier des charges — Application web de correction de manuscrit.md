# Cahier des charges — Application web de correction de manuscrit (v1, prête à coder)

> ⚠️ **DOCUMENT HISTORIQUE — REMPLACÉ** : ce cahier des charges, écrit avant le développement, a été remplacé par **« Architecture application web — v1 (spécification consolidée) »** (même dossier), qui décrit l'application telle que développée (jalons J0-J2.1) et consolide toutes les décisions. Ne pas s'y référer pour coder : seule la spec consolidée fait foi. Ce document est conservé pour l'historique de conception.

> **Objet** : spécification de développement d'une **application web autonome** de correction de textes littéraires (Chapitre, Passage, Extrait), transposant le métier de la fonction Pipeline OpenWebUI (spécification v6, dossier parent) en une application locale d'abord, mise en ligne ensuite.
>
> **Contexte d'usage** : application **privée, mono-utilisateur, dédiée à la relecture d'un manuscrit unique**. Développement 100 % local ; mise en ligne en fin de projet (J5). Aucune donnée ne quitte la machine locale avant la phase de déploiement.
>
> **Source de vérité métier** : `../Architecture fonction correction de texte — v6 (spécification complète).md` (ci-après « v6 »). Toute règle métier de la v6 (§5 à §15) est **reprise telle quelle** sauf mention contraire explicite dans le présent cahier ; en cas de divergence, la v6 prime pour le métier et le présent cahier prime pour l'architecture applicative.

**Sommaire** : 1. Contexte et objectifs · 2. Positionnement par rapport à la fonction OpenWebUI · 3. Décisions d'architecture · 4. Architecture technique · 5. Transposition du métier v6 · 6. Écrans et parcours · 7. Flux de traitement · 8. Exigences non fonctionnelles · 9. Jalons de développement (J0-J5) · 10. Tests et validation · 11. Registre des décisions · 12. Références

* * *

## 1. Contexte et objectifs

### 1.1 Origine

La fonction Pipeline OpenWebUI (v6) a servi de spécification métier complète. L'application web en reprend la totalité de la logique (normalisation, offsets, chaîne $N+1$, codex, RAG alias, déduplication, alertes) en **supprimant les contraintes de plateforme** : plus d'API interne fragile, plus d'Artifact dans une iframe, plus de mini-langage de commandes textuel.

### 1.2 Objectifs

1. **Bibliothèque de manuscrit** : les chapitres officiels, textes soumis et historiques d'analyse sont stockés en base — plus de copier-coller à chaque usage.
2. **Correction multi-phase** : Forme, Style, Technique, Embellissement (v6 §9-12), exécution parallèle, déduplication Style prioritaire.
3. **Codex vivant** : fiches, alias et journaux consultables **et éditables manuellement** dans l'UI.
4. **Chaîne $N+1 visible** : timeline des chapitres officiels, état de la chaîne, reclassement automatique en Extrait sans jamais bloquer (v6 §6.5).
5. **UI de relecture sur mesure** : annotations colorées WCAG AA, tooltips, filtres par pastille, bouton « Lecture Embellissement », navigation clavier.
6. **Local-first** : tout tourne en local ; mise en ligne optionnelle en fin de projet.

### 1.3 Hors périmètre (v1)

* Multi-utilisateur / multi-romans simultanés complexes (un seul projet actif à la fois).
* Éditeur de texte riche intégré (l'auteur écrit ailleurs ; l'application corrige).
* Chunking et découpage de textes longs (v6 §21 : refusé ; seul `max_caracteres` s'applique).
* Synchronisation cloud, mobile, hors-ligne.
* Facturation, quotas, télémétrie.

* * *

## 2. Positionnement par rapport à la fonction OpenWebUI

| Couche v6 | Sort dans l'application |
| --- | --- |
| Métier : normalisation (§8.1), réconciliation (§8.3), déduplication (§8.4), machine d'états (§6.5), RAG alias (§6.4), alertes et numérotation (§6.7), relecture-diff (§6.6), schéma SQLite (§6.2) | **Réutilisé à ~100 %** — code métier quasi identique |
| Phase 1 : parsing des commandes textuelles (§5) | **Remplacé** par formulaires et boutons (E3, §6 du présent cahier) |
| Phase 7 : générateur HTML autonome (§13) | **Remplacé** par composants serveur Jinja2 + interactivité Alpine.js — les contraintes d'Artifact disparaissent |
| Étanchéité Artifacts (§2.4 v6) : triple saut de ligne, bloc ` ```html `, IIFE, garde-fou backticks | **Supprimée intégralement** — le HTML est servi directement ; l'échappement HTML universel (`html.escape`) est **conservé** ; le garde-fou backticks devient inutile (plus de bloc markdown) |
| `pipe()` / `inlet()` (§2.1 v6) | **Remplacés** par routes FastAPI + jobs asynchrones (§4.4 du présent cahier) |
| Fail-fast ping (§4 v6) | **Conservé** — écran d'erreur avant lancement du job, zéro token consommé |
| Option B (§14.2 v6) | **Conservée** — job marqué « échoué », aucun document partiel, aucune écriture narrative |
| Valves OpenWebUI (§2.2 v6) | **Remplacées** par l'écran Paramètres (E8) + fichier `.env` pour les clés |

* * *

## 3. Décisions d'architecture (arbitrages par défaut, réversibles)

| # | Décision | Choix retenu | Justification / Alternative écartée |
| --- | --- | --- | --- |
| A1 | Backend | **Python 3.11+ / FastAPI / Uvicorn** | La v6 est écrite en termes Pydantic + asyncio + sqlite3 : réutilisation maximale du métier. Alternative (Node) écartée : réécriture totale. |
| A2 | Frontend | **Jinja2 + HTMX + Alpine.js** (pas de build Node) | Assez pour tooltips, pastilles filtres, bouton « Lecture Embellissement », navigation clavier. Alternative SvelteKit écartée pour v1 (complexité sans besoin identifié) — réversible si éditeur riche requis un jour. |
| A3 | Base de données | **SQLite (WAL, busy_timeout)** — schéma v6 §6.2 avec renommages (§5.5) | Mono-utilisateur : SQLite suffit même en ligne. Postgres réservé à un hypothétique multi-utilisateur. |
| A4 | Couche LLM | **Client maison compatible OpenAI** (`httpx`) — endpoints `/v1/chat/completions` | **Décision de l'auteur (post-J1) : fournisseur unique Mistral par clé API, `mistral-small-latest` pour toutes les phases — l'application ne fonctionne QUE par clé API, aucun LLM local.** Le client reste compatible OpenAI si le fournisseur change un jour. LiteLLM écarté (dépendance lourde pour 5 modèles). |
| A5 | Clés API | **Fichier `.env` local, jamais commité** (`.env.example` fourni) | Sécurité ; aucune clé en base ni dans le code. |
| A6 | Jobs | **Tâches `asyncio` en arrière-plan + table d'état** ; polling HTMX côté page | Simplicité ; pas de Celery/Redis en v1. |
| A7 | Versioning | **Git**, un commit par jalon validé | Retour arrière à coût nul. |
| A8 | Conteneurisation | **Docker + docker-compose dès J0** (dev = prod) | Parité dev/prod pour la mise en ligne J5. |
| A9 | Authentification | **Aucune en local** ; à la mise en ligne (J5) : auth simple (mot de passe unique ou basic auth derrière Caddy) | Mono-utilisateur privé. |

* * *

## 4. Architecture technique

### 4.1 Vue d'ensemble

```
[Navigateur]
  |  HTML (Jinja2) + HTMX + Alpine.js
  v
[FastAPI / Uvicorn]
  |--- routes web (écrans E1-E9, §6)
  |--- routes API (JSON) : lancement d'analyse, statut job, actions (choix d'auteur, remplacement...)
  |
  |--- SERVICES MÉTIER (repris de la v6)
  |      |- normalisation / paragraphes / offsets (v6 §8.1, §8.3)
  |      |- machine d'états chaîne $N+1 + reclassement (v6 §6.5)
  |      |- RAG alias (v6 §6.4)          |- alertes + numérotation (v6 §6.7)
  |      |- réconciliation / déduplication (v6 §8.3-8.5)
  |      |- rendu des corrections (v6 §7, adapté en composants serveur)
  |
  |--- COUCHE LLM (httpx, compatible OpenAI)
  |      |- ping fail-fast (v6 §4)       |- phases 2 à 6 parallèles (v6 §14.1)
  |      |- nettoyage fences + Pydantic (v6 §8.5)
  |
  v
[SQLite WAL]  [backups/]  [logs/]
```

### 4.2 Arborescence du projet

```
correction-app/
├── .env.example            # clés API (modèle), jamais le .env réel
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml          # dépendances : fastapi, uvicorn, jinja2, httpx, pydantic-settings, pytest
├── app/
│   ├── main.py             # application FastAPI, démarrage idempotent (v6 §3)
│   ├── config.py           # paramètres (.env) : providers, timeouts, max_caracteres...
│   ├── db.py               # connexion SQLite, WAL, busy_timeout, asyncio.to_thread
│   ├── models.py           # schémas Pydantic (corrections LLM, deltas relecture-diff, alertes)
│   ├── services/
│   │   ├── normalisation.py      # §8.1 v6
│   │   ├── chaine.py             # machine d'états $N+1, reclassement, /maj (§6.5-6.6 v6)
│   │   ├── codex.py              # RAG alias, fiches, journaux (§6.4 v6)
│   │   ├── alertes.py            # numérotation, choix d'auteur, double barrière (§6.7 v6)
│   │   ├── analyse.py            # orchestration phases 2-6, fail-fast, Option B (§4, §14 v6)
│   │   ├── reconciliation.py     # offsets, déduplication Style prioritaire (§8.3-8.5 v6)
│   │   └── rendu.py              # fusion, groupes g-XXXX, annotations (§7, §13 v6)
│   ├── llm/
│   │   ├── client.py             # client compatible OpenAI, timeout, retries
│   │   └── prompts.py            # prompts des phases 2-6 (fences anti-injection v6 §2.3)
│   ├── routes/
│   │   ├── web.py                # écrans E1-E9
│   │   └── api.py                # actions et statuts
│   └── templates/ + static/      # Jinja2, HTMX, Alpine, CSS (palette v6 §7.2)
├── tests/
│   ├── unit/                     # métier pur : normalisation, offsets, chaîne, dédup
│   └── integration/              # LLM mocké (réponses enregistrées), scénarios complets
├── data/                         # database.sqlite3, backups/, logs/ (ignoré par git)
└── exports/                      # exports md/docx
```

### 4.3 Couche LLM

* **Configuration par phase** (équivalent des Valves v6 §2.2) : chaque phase (2 à 6) a son modèle, sa température (`0.0` pour 2-5, `0.8` pour 6), son timeout (`timeout_phase`, défaut 90 s), éditables dans E8.
* **Ping fail-fast** (v6 §4) : `/v1/models` ou requête `max_tokens=5`, parallèle, `retries_ping` nouvelles tentatives ; en cas d'échec, **le job n'est pas lancé** — écran d'erreur, zéro token d'analyse.
* **Anti-injection** (v6 §2.3) : manuscrit et codex délimités par fences explicites avec consigne de non-obéissance.
* **Nettoyage + validation** (v6 §8.5) : retrait des fences `` ```json ``, Pydantic `extra='forbid'`, rejet par entrée sans arrêt ; **une liste valide vide n'est jamais une panne**.

### 4.4 Jobs asynchrones

1. La soumission d'un texte crée un enregistrement `analyses` (statut : `en_attente`).
2. Un worker `asyncio` exécute la séquence du §7 (chaîne → fail-fast → phases parallèles → validation → dédup → écritures → rendu).
3. Statuts : `en_attente` → `en_cours` (étape courante affichée) → `terminee` | `echec` (Option B) | `rejetee` (fail-fast).
4. La page d'analyse (E4) rafraîchit le statut par polling HTMX ; l'utilisateur ne peut pas obtenir de résultat partiel.
5. **Aucune écriture narrative ni alerte avant l'étape d'écriture finale** (v6 §14.1 étape 11) — un job échoué ne laisse aucune trace narrative.

## 5. Transposition du métier v6

### 5.1 Table de correspondance

| Règle v6 | Module applicatif | Adaptation |
| --- | --- | --- |
| §5.2 Détection de catégorie (titre première ligne, Prologue, seuils) | `services/normalisation.py` + formulaire E3 | Détection automatique conservée ; **l'UI permet toujours de corriger la catégorie proposée** avant lancement (équivalent `/passage`, `/extrait`) |
| §5.4 Matrice d'activation phases 3-6 | E3 (cases à cocher pré-cochées selon la matrice) | L'utilisateur peut activer `/style`, `/technique`, `/embellissement` par cases ; les commandes redondantes deviennent des options désactivées avec infobulle explicative |
| §6.5 Machine d'états $N+1$, rupture → Extrait | `services/chaine.py` | Identique ; la bannière `reclassement_extrait` s'affiche en page de résultat |
| §6.6 `/maj` = remplacement officiel | Bouton « Remplacer le chapitre N » (E3, dialogue de confirmation) | Préconditions identiques : N déjà soumis ET N = chapitre courant ; sinon refus explicite avant analyse, zéro token |
| §6.4 RAG alias, §6.7 alertes + choix d'auteur | `services/codex.py`, `services/alertes.py` | Identiques ; `/nopb` devient le bouton « Choix d'auteur » sur chaque alerte du bandeau |
| §8.1 Normalisation, §8.3 réconciliation, §8.4 déduplication (Style prioritaire), §8.5 validation | `services/normalisation.py`, `reconciliation.py` | Identiques, mot pour mot |
| §7 Rendu des corrections + §7.4 bouton « Lecture Embellissement » | `services/rendu.py` + templates | Annotations identiques (palette §7.2, tooltips, `<del>`/`<ins>`/`<mark>`) ; le bouton devient un vrai bouton Alpine ; plus de contraintes d'Artifact |
| §14.1 Séquence, §14.2 incidents | `services/analyse.py` + §7 du présent cahier | Identique, adapté aux jobs |

### 5.2 Catégorisation sans commandes

* La détection automatique (v6 §5.2) s'applique au texte collé et **pré-sélectionne** la catégorie dans E3.
* L'utilisateur peut forcer **Passage** ou **Extrait** avant lancement (boutons radio) — exactement `/passage` et `/extrait`, sans syntaxe à retenir.
* **Aucun mini-langage** : toutes les commandes v6 ont un équivalent UI (table de correspondance ci-dessus).

### 5.3 Chaîne $N+1$ et remplacement

* La machine d'états v6 §6.5 est reprise intégralement : conforme → écritures ; **N=N sans remplacement → rupture → Extrait** (bannière + `chain_status='rupture'`) ; N=N **avec remplacement explicite** (bouton) → relecture-diff + remplacement du texte stocké + correction livrée.
* La timeline (E2) rend la chaîne visible : chaque chapitre officiel, son statut, le numéro attendu suivant, les textes reclassés.

### 5.4 Rendu des corrections

* Reprise de la v6 §7 : seuls les paragraphes corrigés affichés + compteur « X paragraphes sans correction non affichés », tooltips multi-cas, ordre Forme → Style → Technique → Embellissement, `<mark class="sugg">` jamais barré, bouton « Lecture Embellissement » (visible si la Phase 6 a produit des suggestions).
* **Différence** : le rendu est un template Jinja2 servi par FastAPI — l'échappement HTML universel est conservé ; la contrainte de bloc ` ```html ` et le garde-fou backticks disparaissent.

### 5.5 Schéma de données (renommages v6 → application)

Le schéma SQL de la v6 §6.2 est repris avec les renommages suivants (mono-utilisateur local) :

| v6 | Application | Note |
| --- | --- | --- |
| `sessions` / `session_id` | `projets` / `projet_id` | Un projet = un roman |
| `sessions.user_id` | *(supprimé)* | Mono-utilisateur local ; l'isolation par utilisateur redeviendra pertinente à la mise en ligne (J5) |
| `etat_utilisateur` | `parametres` (clé/valeur, dont `projet_actif`) | Le pointeur de projet actif + réglages persistés |
| `chapitres`, `codex`, `codex_index`, `journaux` | identiques (colonnes `session_id` → `projet_id`) | SQL v6 §6.2 au renommage près |
| `alertes.numero_session` | `alertes.numero_projet` | Numérotation stable identique (MAX+1 à l'insertion) |
| — | `analyses` *(nouvelle)* | `id`, `projet_id`, `texte_source`, `statut`, `etape`, `categorie`, `resultat_ref`, `erreur`, horodatages — support des jobs (§4.4) |
| — | `corrections` *(nouvelle, optionnelle)* | Dernier jeu de corrections fusionnées par analyse (historique de relecture) |

* Toutes les règles v6 §6.5 (périmètre des écritures par table), §15 (backups `Connection.backup()` natif avant écritures narratives, WAL, `busy_timeout`, `asyncio.to_thread`) s'appliquent telles quelles.

## 6. Écrans et parcours (spécification UI)

**Palette et accessibilité** : reprise intégrale de la v6 §7.2 (couleurs WCAG AA) et §7.5 (navigation clavier `←`/`→`/`Échap`, `aria-pressed`, `tabindex`).

### E1 — Accueil / Projets
* Liste des projets (romans) : titre, chaîne d'état (`vierge`/`ok`/`rupture`), chapitre courant, nombre d'alertes actives.
* Création d'un projet ; **projet actif** unique (équivalent `parametres.projet_actif`, v6 `etat_utilisateur`) ; suppression avec confirmation en 2 étapes + backup préalable (v6 §6.3) ; refus de supprimer le projet actif.

### E2 — Bibliothèque de chapitres (timeline de la chaîne)
* Vue chronologique : Prologue (0), chapitres 1..N officiels, textes reclassés en Extrait (grisés, marqués « hors chaîne »).
* Par chapitre : numéro, titre, date, hash différent de la version précédente (si remplacement), lien vers la dernière analyse.
* **Numéro attendu suivant** affiché en évidence — la règle $N+1$ devient visible (v6 §6.5).

### E3 — Soumission d'un texte
* Zone de collage du texte + garde-fou `max_caracteres` (compteur live, refus explicite au-delà — v6 §2.3).
* **Catégorie proposée automatiquement** (v6 §5.2), modifiable par boutons radio : Chapitre / Passage / Extrait.
* Cases d'activation des phases (pré-cochées selon la matrice v6 §5.4) : Style, Technique, Embellissement — incohérences signalées à la volée.
* Bouton « Remplacer le chapitre courant » (équivalent `/maj`, v6 §6.6) avec dialogue de confirmation ; refus explicite si le chapitre courant n'existe pas encore.
* Bouton « Lancer l'analyse » → création du job → redirection vers E4.

### E4 — Suivi d'analyse (job)
* Statut en temps réel (polling HTMX) : étapes de la séquence §7 (chaîne → fail-fast → phases → validation → écritures → rendu).
* **Rejet fail-fast** : écran d'erreur clair, modèle fautif, cause, zéro token consommé — rien n'est écrit (v6 §4.2).
* **Échec Option B** : écran d'échec, cause, référence de log — aucun document partiel (v6 §14.2).

### E5 — Résultat de correction (écran central)
* **Document annoté** : seuls les paragraphes corrigés + compteur « X paragraphes sans correction non affichés » (v6 §7.1).
* Légende interactive : pastilles Forme/Style/Technique/Embellissement (`aria-pressed`) + **bouton « Lecture Embellissement »** (v6 §7.4).
* Tooltips multi-cas avec variantes ordonnées (v6 §7.3), y compris sections « Embellissement — suggestions » hébergées par les corrections Style (v6 §8.4).
* **Bandeau d'alertes numérotées** (`numero_projet`, v6 §6.7) : niveau, code, motif, bouton **« Choix d'auteur »** (= `/nopb`) par alerte.
* Bannière `reclassement_extrait` le cas échéant (v6 §6.5).
* Pied de page : projet actif, catégorie finale, statut de chaîne.
* Actions : relancer, exporter (E9).

### E6 — Codex
* Fiches par catégorie (`glossaire`, `personnage`, `linguistique`, `rang`, `fraction`, `epoque`), alias associés.
* **Éditeur manuel** : créer/modifier une fiche, gérer les alias (alimentant `codex_index` pour le RAG v6 §6.4).

### E7 — Journaux
* Journaux `ecriture`, `evolution`, `intrigue` par entité et global (v6 §6.2) ; lecture seule.

### E8 — Paramètres
* Par phase (2-6) : modèle, température, timeout ; `variante` linguistique ; `timeout_ping`, `retries_ping`, `backups_max`, `mode_debug`, `max_caracteres`.
* Providers LLM : URL de base + clé (**via `.env` uniquement** — l'UI teste la connexion, n'affiche jamais la clé).
* Bouton « Tester les modèles » (= ping fail-fast sans consommation d'analyse).

### E9 — Outils
* **Backups** : liste des sauvegardes `backups/database-YYYYMMDD-HHMMSS.sqlite3`, restauration avec confirmation, purge selon `backups_max` (v6 §15).
* **Exports** : texte corrigé (substitution appliquée) et rapport en Markdown / DOCX.
* **Statistiques** : corrections par phase, alertes validées, tokens estimés par analyse (si le provider le rapporte).
* **Logs debug** : consultation des journaux quotidiens si `mode_debug` actif (v6 §2.5).

* * *

## 7. Flux de traitement (adaptation de la v6 §14.1)

1. **Soumission (E3)** → normalisation (v6 §8.1), catégorisation provisoire, création du job `analyses`.
2. **Validation du remplacement** : si « Remplacer le chapitre courant » coché → préconditions v6 §6.6 (chapitre existant, N=N) ; sinon refus zéro token.
3. **Chaîne (sans LLM)** : chargement du projet actif, arbitrage v6 §6.5 → catégorie définitive (conforme ou reclassée en Extrait, `chain_status` mis à jour — métadonnée sans backup).
4. **Fail-fast** : ping parallèle des modèles requis par la matrice définitive + test SQLite (v6 §4). Échec → job `rejetee`, écran explicite, zéro token.
5. **Phase 2 (analyse LLM)** : RAG alias, cohérence → alertes ; relecture-diff si remplacement (v6 §6.6).
6. **Phases 3 à 6** : parallèles sur le texte normalisé immuable (v6 §8.1). **Toute panne → job `echec` (Option B)** : aucun résultat partiel, aucune écriture narrative ni alerte.
7. **Validation & réconciliation** : nettoyage fences, Pydantic strict, recalcul offsets, rejets individuels sans arrêt ; **une liste valide vide n'est jamais une panne** (v6 §8.5).
8. **Déduplication** : priorité Style, migration des suggestions Embellissement en variantes de tooltip (v6 §8.4).
9. **Écritures finales** : backup natif SQLite puis transaction (codex/journaux/chapitres pour chapitres conformes et remplacements uniquement) **+ persistance des alertes toutes catégories** (v6 §6.5). Échec SQLite → `ROLLBACK`, résultat HTML quand même livré + alerte `persistance_echouee`.
10. **Rendu (E5)** : document annoté, bandeau, légende interactive.
11. **Fin de job** : statut `terminee`, lien depuis E2/E5.

**Règle d'asymétrie (v6 §14.2)** : anomalies utilisateur (chaîne, préconditions) → mode protecteur (Extrait/rejet ciblé), jamais de blocage de la correction ; pannes runtime → arrêt total du job (résultats non fiables).

* * *

## 8. Exigences non fonctionnelles

| Exigence | Détail |
| --- | --- |
| **Local-first** | Code et données 100 % locaux ; les analyses passent par l'API Mistral (clé dans `.env`, décision de l'auteur : clé API uniquement) ; aucune télémétrie ; aucun CDN (HTMX/Alpine servis localement) ; polices système. |
| **Sécurité** | Clés API uniquement dans `.env` (git-ignoré) ; échappement HTML universel de tout contenu LLM/manuscrit ; aucune exécution de contenu soumis. |
| **Persistance robuste** | WAL, `busy_timeout=15000`, `integrity_check` au démarrage, backups `Connection.backup()` natifs avant écritures narratives, purge `backups_max`, toutes les opérations SQL via `asyncio.to_thread` (v6 §3, §15). |
| **Performance** | Phases 3-6 parallèles ; timeout par phase configurable ; un seul job actif à la fois (mono-utilisateur, verrou applicatif). |
| **Accessibilité** | WCAG AA (palette v6 §7.2), navigation clavier complète, `aria-pressed` sur les toggles, focus visible. |
| **Journalisation** | `logs/debug-YYYY-MM-DD.log` chronométré si `mode_debug` ; toute panne référence son log à l'écran (v6 §2.5). |
| **Idempotence** | Démarrage : création arborescence + tables si absentes (v6 §3). |
| **Langue** | Interface intégralement en français. |
| **Taille des textes** | Pas de chunking ; refus explicite au-delà de `max_caracteres` (défaut 30 000) — jamais de troncature silencieuse. |

* * *

## 9. Jalons de développement (backlog J0-J5)

> **Règle de conduite** : 1 jalon = 1 ou 2 sessions de travail avec Cline = du code testé, commité, **validé par l'auteur sur un vrai chapitre** avant de passer au suivant. Le document v6 fait foi pour le métier ; le présent cahier pour l'application.

### J0 — Socle
* **Contenu** : init repo git ; `pyproject.toml` ; squelette FastAPI + Jinja2 ; `db.py` (WAL, busy_timeout, to_thread, initialisation idempotente) ; **schéma SQLite complet** (v6 §6.2 + renommages §5.5) ; page d'accueil E1 minimale ; Dockerfile + compose ; `.env.example`.
* **Critères d'acceptation** : `uvicorn` démarre ; `pytest` verts sur le schéma (création, contraintes, `ON DELETE RESTRICT/CASCADE`) ; `docker compose up` fonctionnel.

### J1 — Moteur métier (cœur v6, sans UI)
* **Contenu** : `normalisation.py` (§8.1) ; `reconciliation.py` (offsets §8.3, dédup §8.4, validation §8.5) ; `chaine.py` (§6.5, §6.6 préconditions) ; `alertes.py` (§6.7 numérotation + double barrière) ; client LLM compatible OpenAI (ping, timeouts, nettoyage fences) ; **mock LLM** pour les tests.
* **Critères d'acceptation** : tests unitaires verts — CRLF/BOM, découpage paragraphes, offsets décalés réconciliés, rejet des corrections introuvables, déduplication Style prioritaire (exact vs partiel), machine d'états (conforme / N=N sans remplacement → Extrait / remplacement valide / refus), numérotation stable, **liste vide valide jamais une panne**, panne → Option B.

### J2 — MVP de relecture
* **Contenu** : E3 (soumission, catégorisation auto, matrice de cases, garde-fou taille) ; jobs (§4.4) ; phases 3-6 parallèles avec Ollama ou provider réel ; E4 (suivi) ; E5 (résultat : annotations, tooltips, pastilles filtres, bouton « Lecture Embellissement », compteur paragraphes masqués).
* **Critères d'acceptation** : **l'auteur corrige son premier vrai chapitre dans le navigateur**, tooltips et filtres fonctionnels, échec de phase → job échoué sans résultat partiel.

### J3 — Chaîne & codex
* **Contenu** : E2 (timeline, numéro attendu) ; reclassement automatique + bannière ; bouton « Remplacer le chapitre courant » (relecture-diff, remplacement du texte stocké) ; RAG alias ; Phase 2 cohérence + bandeau d'alertes + bouton « Choix d'auteur » ; E6 (codex éditable) ; E7 (journaux).
* **Critères d'acceptation** : scénario complet réel — Prologue → chapitre 1 → chapitre 2 → resoumission N=N sans remplacement (→ Extrait, codex intact) → remplacement officiel (codex mis à jour, évolutions historisées) → alerte détectée → « Choix d'auteur » → **non re-détectée à la resoumission**.

### J4 — Confort
* **Contenu** : E9 complet (backups + restauration, exports md/docx, statistiques) ; E8 (paramètres + test de connexion) ; mode debug UI.
* **Critères d'acceptation** : export du chapitre corrigé fidèle ; restauration d'un backup testée ; statistiques cohérentes.

### J5 — Mise en ligne
* **Contenu** : durcissement (auth simple, en-têtes de sécurité) ; Caddy (TLS automatique) ; compose de production avec volumes persistants ; sauvegardes programmées ; documentation de déploiement VPS ; **option Tailscale documentée** (accès distant sans exposition publique).
* **Critères d'acceptation** : accès HTTPS depuis l'extérieur ; restauration d'un backup depuis le VPS ; doc de déploiement pas-à-pas validée.

* * *

## 10. Tests et validation

| Niveau | Contenu | Outils |
| --- | --- | --- |
| **Unitaires** (J1+) | Normalisation, paragraphes, offsets, réconciliation, déduplication, machine d'états, numérotation, périmètre des écritures | `pytest` + fixtures textuelles (texte CRLF, offsets décalés, chevauchements exacts/partiels) |
| **Intégration** (J1-J2) | Séquence complète avec LLM mocké (réponses JSON réelles enregistrées) : fail-fast, Option B, liste vide, relecture-diff | `pytest` + client ASGI (`httpx`) |
| **E2E manuel** (J2+) | Chaque jalon validé par l'auteur sur un vrai chapitre du manuscrit, avec retour visuel (captures si bug d'affichage) | Navigateur |
| **Stratégie LLM** | Tests : Mock LLM déterministe (coût nul) ; exécution réelle : **Mistral Small par clé API** (décision de l'auteur — aucun LLM local) ; vérification de la connexion : `scripts/tester_llm.py` | `.env` |

## 11. Registre des décisions

1. **Source de vérité** : la v6 est le cahier des charges métier ; ce document est le cahier des charges applicatif. En cas de divergence : v6 prime pour le métier, ce document prime pour l'architecture.
2. **Stack** : FastAPI + Jinja2 + HTMX + Alpine.js + SQLite — choix de simplicité (A1-A3), SvelteKit écarté en v1 mais réversible.
3. **Couche LLM** : client maison compatible OpenAI (`httpx`) — **fournisseur unique Mistral par clé API** (`mistral-small-latest`, décision de l'auteur post-J1 : aucun LLM local) (A4) ; clés exclusivement dans `.env` (A5).
4. **Renumérotations** : sessions → **projets**, `user_id` supprimé en local (réintroduit en J5 si nécessaire), `numero_session` → `numero_projet`.
5. **Fin du mini-langage** : toutes les commandes v6 deviennent des éléments d'UI (radio catégorie, cases de phases, bouton « Remplacer le chapitre courant », bouton « Choix d'auteur »).
6. **Fin des contraintes d'Artifact** : plus de triple saut de ligne, plus de bloc ` ```html `, plus d'IIFE obligatoire, plus de garde-fou backticks ; l'échappement HTML universel est conservé.
7. **Métier intact** : normalisation, offsets, réconciliation, déduplication Style prioritaire, machine d'états $N+1$ (N=N sans remplacement → Extrait), relecture-diff, RAG alias, alertes numérotées à double barrière, Option B, fail-fast, backups natifs — repris mot pour mot de la v6.
8. **Jobs asynchrones** : un job à la fois, statuts visibles, aucune écriture narrative ni alerte avant l'étape finale d'écriture (A6).
9. **Jalons** : J0 socle → J1 moteur → J2 MVP relecture → J3 chaîne & codex → J4 confort → J5 mise en ligne (Docker + Caddy + auth simple, option Tailscale).
10. **Méthode** : git par jalon, tests pytest dès J1, validation de l'auteur sur vrais chapitres à chaque jalon, développement avec Ollama puis bascule provider.

## 12. Références

| Document | Emplacement |
| --- | --- |
| Spécification métier v6 (source de vérité) | `../Architecture fonction correction de texte — v6 (spécification complète).md` |
| Versions antérieures (historique des arbitrages) | `../Architecture fonction correction de texte — v3/v4/v5.md` |
| Présent cahier des charges | `./Cahier des charges — Application web de correction de manuscrit.md` |

*Sections v6 citées* : §2.3 (anti-injection, max_caracteres), §2.5 (debug), §3 (persistance), §4 (fail-fast), §5.2-5.4 (catégorisation, matrice), §6.2-6.7 (schéma, sessions, RAG, chaîne, /maj, alertes), §7.1-7.5 (rendu, palette, filtres, clavier), §8.1-8.5 (normalisation, offsets, déduplication, validation), §9-13 (phases, générateur), §14.1-14.2 (séquence, incidents), §15 (backups SQLite).

