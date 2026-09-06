"""Tests du schéma SQLite (critère d'acceptation J0 : création, contraintes, RESTRICT/CASCADE)."""

import sqlite3

import pytest

TABLES_ATTENDUES = {
    "projets",
    "parametres",
    "chapitres",
    "codex",
    "codex_index",
    "journaux",
    "alertes",
    "analyses",
    "corrections",
}


def test_toutes_les_tables_existent(connexion):
    lignes = connexion.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    tables = {ligne[0] for ligne in lignes}
    assert TABLES_ATTENDUES <= tables, f"Tables manquantes : {TABLES_ATTENDUES - tables}"


def test_initialisation_idempotente(base_donnees):
    from app import db

    db.init_db()  # relancer ne doit ni échouer ni dupliquer
    connexion2 = sqlite3.connect(base_donnees)
    try:
        lignes = connexion2.execute("SELECT COUNT(*) FROM projets").fetchone()
        assert lignes[0] == 0
    finally:
        connexion2.close()


def test_cascade_suppression_projet(connexion):
    connexion.execute(
        "INSERT INTO projets (projet_id, titre) VALUES ('P-TEST01', 'Roman test')"
    )
    connexion.execute(
        "INSERT INTO codex (projet_id, category, entity_name, data_json) "
        "VALUES ('P-TEST01', 'personnage', 'Aria', '{}')"
    )
    connexion.execute("DELETE FROM projets WHERE projet_id = 'P-TEST01'")
    restant = connexion.execute(
        "SELECT COUNT(*) FROM codex WHERE projet_id = 'P-TEST01'"
    ).fetchone()[0]
    assert restant == 0, "La suppression d'un projet doit cascader sur le codex"


def test_projet_actif_insupprimable_puis_supprimable(connexion):
    """Équivalent du ON DELETE RESTRICT v6 : trigger sur parametres.projet_actif."""
    connexion.execute(
        "INSERT INTO projets (projet_id, titre) VALUES ('P-ACTIF1', 'Projet actif')"
    )
    connexion.execute(
        "INSERT INTO parametres (cle, valeur) VALUES ('projet_actif', 'P-ACTIF1')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        connexion.execute("DELETE FROM projets WHERE projet_id = 'P-ACTIF1'")

    # Changement de projet actif -> la suppression devient possible
    connexion.execute("UPDATE parametres SET valeur = 'P-AUTRE' WHERE cle = 'projet_actif'")
    connexion.execute("DELETE FROM projets WHERE projet_id = 'P-ACTIF1'")
    assert (
        connexion.execute("SELECT COUNT(*) FROM projets WHERE projet_id = 'P-ACTIF1'").fetchone()[0]
        == 0
    )


def test_uniques_codex_et_alertes(connexion):
    connexion.execute(
        "INSERT INTO projets (projet_id, titre) VALUES ('P-TEST02', 'Roman test')"
    )
    connexion.execute(
        "INSERT INTO codex (projet_id, category, entity_name, data_json) "
        "VALUES ('P-TEST02', 'personnage', 'Aria', '{}')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        connexion.execute(
            "INSERT INTO codex (projet_id, category, entity_name, data_json) "
            "VALUES ('P-TEST02', 'personnage', 'Aria', '{}')"
        )

    connexion.execute(
        "INSERT INTO alertes (projet_id, numero_projet, niveau, code, motif) "
        "VALUES ('P-TEST02', 1, 'information', 'incoherence_potentielle', 'Test')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        connexion.execute(
            "INSERT INTO alertes (projet_id, numero_projet, niveau, code, motif) "
            "VALUES ('P-TEST02', 1, 'information', 'incoherence_potentielle', 'Doublon')"
        )


def test_checks_enums(connexion):
    with pytest.raises(sqlite3.IntegrityError):
        connexion.execute(
            "INSERT INTO projets (projet_id, titre, chain_status) "
            "VALUES ('P-BAD01', 'Mauvais', 'bizarre')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        connexion.execute(
            "INSERT INTO alertes (projet_id, numero_projet, niveau, code, motif) "
            "VALUES ('P-BAD02', 1, 'critique', 'code', 'Niveau invalide')"
        )
