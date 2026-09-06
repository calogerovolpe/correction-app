-- Schéma SQLite — cahier des charges §5.5 (v6 §6.2 au renommage près : sessions→projets).
-- Mono-utilisateur local : user_id supprimé ; numéro attendu/chaîne : v6 §6.5.

CREATE TABLE IF NOT EXISTS projets (
  projet_id           TEXT PRIMARY KEY,          -- Format P-XXXXXX (base36)
  titre               TEXT NOT NULL,
  current_chapter_num INTEGER,                   -- NULL si vierge ; 0 pour Prologue
  last_chapter_title  TEXT,
  chain_status        TEXT NOT NULL DEFAULT 'vierge'
                      CHECK (chain_status IN ('vierge', 'ok', 'rupture')),
  created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Pointeur de projet actif + réglages persistés (v6 etat_utilisateur, renommé)
CREATE TABLE IF NOT EXISTS parametres (
  cle    TEXT PRIMARY KEY,
  valeur TEXT NOT NULL
);

-- Équivalent du ON DELETE RESTRICT de la v6 : impossible de supprimer le projet actif
CREATE TRIGGER IF NOT EXISTS trg_projet_actif_restrict
BEFORE DELETE ON projets
WHEN EXISTS (SELECT 1 FROM parametres WHERE cle = 'projet_actif' AND valeur = OLD.projet_id)
BEGIN
  SELECT RAISE(ABORT, 'SUPPRESSION_REFUSEE_PROJET_ACTIF');
END;

-- Texte normalisé des chapitres officiels (relecture-diff du remplacement, v6 §6.6)
CREATE TABLE IF NOT EXISTS chapitres (
  projet_id TEXT NOT NULL REFERENCES projets(projet_id) ON DELETE CASCADE,
  numero    INTEGER NOT NULL,
  texte     TEXT NOT NULL,
  hash      TEXT NOT NULL,                      -- SHA-256 du texte normalisé
  soumis_a  TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (projet_id, numero)
);

CREATE TABLE IF NOT EXISTS codex (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  projet_id   TEXT NOT NULL REFERENCES projets(projet_id) ON DELETE CASCADE,
  category    TEXT NOT NULL,                    -- 'glossaire'|'personnage'|'linguistique'|'rang'|'fraction'|'epoque'
  entity_name TEXT NOT NULL,
  data_json   TEXT NOT NULL,
  UNIQUE(projet_id, category, entity_name)
);
CREATE INDEX IF NOT EXISTS idx_codex_entity ON codex(projet_id, entity_name);

CREATE TABLE IF NOT EXISTS codex_index (
  alias       TEXT NOT NULL,
  projet_id   TEXT NOT NULL REFERENCES projets(projet_id) ON DELETE CASCADE,
  entity_type TEXT NOT NULL,
  entity_name TEXT NOT NULL,
  UNIQUE(projet_id, alias, entity_name)
);
CREATE INDEX IF NOT EXISTS idx_alias ON codex_index(projet_id, alias);

CREATE TABLE IF NOT EXISTS journaux (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  projet_id   TEXT NOT NULL REFERENCES projets(projet_id) ON DELETE CASCADE,
  category    TEXT NOT NULL,                     -- 'ecriture'|'evolution'|'intrigue'
  entity_name TEXT,                             -- NULL pour journal global
  data_json   TEXT NOT NULL
);

-- Numérotation stable portée par le projet (v6 §6.7) : MAX+1 à l'insertion, jamais de glissement
CREATE TABLE IF NOT EXISTS alertes (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  projet_id     TEXT NOT NULL REFERENCES projets(projet_id) ON DELETE CASCADE,
  numero_projet INTEGER NOT NULL,
  niveau        TEXT NOT NULL CHECK (niveau IN ('avertissement', 'information', 'confirmation')),
  code          TEXT NOT NULL,
  cible         TEXT,                            -- cible de l'alerte : double barrière /nopb (v6 §6.7)
  motif         TEXT NOT NULL,
  statut        TEXT NOT NULL DEFAULT 'active' CHECK (statut IN ('active', 'validee')),
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(projet_id, numero_projet)
);
CREATE INDEX IF NOT EXISTS idx_alertes_projet ON alertes(projet_id, statut);

-- Support des jobs asynchrones (cahier des charges §4.4)
CREATE TABLE IF NOT EXISTS analyses (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  projet_id    TEXT NOT NULL REFERENCES projets(projet_id) ON DELETE CASCADE,
  texte_source TEXT NOT NULL,
  statut       TEXT NOT NULL DEFAULT 'en_attente'
               CHECK (statut IN ('en_attente', 'en_cours', 'terminee', 'echec', 'rejetee')),
  etape        TEXT,
  categorie    TEXT,
  options_json TEXT,                            -- options du formulaire E3 (catégorie, phases, remplacement)
  decision     TEXT,                            -- décision de la machine d'états (conforme, reclassement_extrait…)
  message      TEXT,                            -- message de bannière éventuel (reclassement)
  resultat_ref TEXT,
  erreur       TEXT,
  cree_a       TEXT NOT NULL DEFAULT (datetime('now')),
  fini_a       TEXT
);

-- Historique de relecture : dernier jeu de corrections fusionnées par analyse
CREATE TABLE IF NOT EXISTS corrections (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  analyse_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  data_json  TEXT NOT NULL,
  cree_a     TEXT NOT NULL DEFAULT (datetime('now'))
);
