# Fichiers protégés et interdits

## NE JAMAIS MODIFIER (sans accord explicite de l'auteur)
| Fichier | Raison |
|---|---|
| `.env` | Contient la **clé API Mistral réelle**. Ne jamais l'afficher, le committer, le copier dans un fichier de test ou le lire hors de `config.py`/`scripts/tester_llm.py` |
| `.env.example` | Modèle public (clé factice uniquement) |
| `app/static/vendor/` | Librairies locales HTMX/Alpine — ne pas éditer, ne pas remplacer par des CDN |
| `data/` | Base SQLite + backups + logs de l'auteur (contient son **manuscrit**). Ne jamais supprimer, ni committer (déjà dans `.gitignore`) |
| `app/schema.sql` | Schéma de référence — toute évolution doit être justifiée par la v6/le cahier et être idempotente (`CREATE TABLE IF NOT EXISTS`) |
| `.clinerules/` | Ne pas supprimer ; `README.md` se MET À JOUR à chaque jalon (c'est le journal de bord), les autres fichiers évoluent uniquement sur arbitrage |
| `tests/` existants | Ne jamais supprimer/affaiblir un test pour le faire passer ; un échec = corriger le code ou le test si le comportement attendu a changé (avec justification) |

## NE JAMAIS FAIRE
- Committer `.env`, `data/`, exports/ ou toute clé/token (vérifier `git status` avant commit).
- Changer les couleurs de la palette (WCAG AA, v6 §7.2) ou les règles métier de la v6 sans
  arbitrage explicite de l'auteur.
- Introduire un CDN, une police distante ou une dépendance externe au rendu.
- Appeler l'API Mistral depuis les tests pytest.
- « Réparer » un test en supprimant une assertion (le bug J2.1 de redirection était invisible
  précisément parce que la situation n'était pas testée).
- Modifier le comportement Option B / fail-fast / liste-vide-jamais-panne (garde-fous v6).

## Fichiers de l'auteur (documentation)
- **`docs/Architecture application web — v1 (spécification consolidée).md`** (dans le repo) :
  LA source de vérité de l'application. Versionnée avec le code : toute évolution
  métier/architecturale est committée **dans le même commit** que le code correspondant.
- `docs/Cahier des charges — Application web de correction de manuscrit.md` (dans le repo) :
  historique de conception, remplacé par la spec consolidée (bandeau en tête) — ne pas coder avec.
- Hors repo (dossier grand-parent sur le disque) : `Architecture fonction correction de
  texte — v3/v4/v5/v6.md` — archive de la genèse (fonction OpenWebUI jamais développée) ;
  ne pas coder avec, ne pas copier dans le repo.
- **Le manuscrit de l'auteur** (`data/`, ignoré par git) ne quitte JAMAIS sa machine :
  aucun texte soumis ne doit être committé, exporté ou copié hors de `data/` et `exports/`.

## Points sensibles à traiter avec prudence
- `app/routes/web.py` : le déballage de `db.executer` (bug historique J2.1).
- `app/db.py` : le verrou `threading.Lock` est un choix délibéré (cf. 02-conventions).
- `app/main.py` : la récupération des jobs orphelins au démarrage ne doit jamais être retirée.
