"""Tests des alertes — v6 §6.7 : numérotation stable, choix d'auteur, double barrière."""

import asyncio
import json

from app.models import AlerteDetectee


def _run(coro):
    return asyncio.run(coro)


def _initialiser():
    from app import db

    db.init_db()
    _run(db.executer("INSERT INTO projets (projet_id, titre) VALUES ('P-TEST', 'Roman')", ()))
    return db


def _alerte(code="incoherence_confirmee", niveau="avertissement", cible="Aria", motif="Blessure disparue"):
    return AlerteDetectee(code=code, niveau=niveau, cible=cible, motif=motif)


def test_numerotation_stable_meme_apres_validation(dossier_donnees):
    db = _initialiser()
    from app.services import alertes

    n1 = _run(alertes.creer("P-TEST", _alerte()))
    n2 = _run(alertes.creer("P-TEST", _alerte(code="incoherence_potentielle", niveau="information", cible="Kael", motif="Anachronisme")))
    assert (n1, n2) == (1, 2)

    assert _run(alertes.valider_choix_auteur("P-TEST", 1)) is True

    # Aucun glissement après validation : la prochaine alerte prend 3 (v6 §6.7)
    n3 = _run(alertes.creer("P-TEST", _alerte(motif="Autre cas")))
    assert n3 == 3


def test_choix_auteur_archivé_dans_journal_intrigue(dossier_donnees):
    db = _initialiser()
    from app.services import alertes

    _run(alertes.creer("P-TEST", _alerte()))
    assert _run(alertes.valider_choix_auteur("P-TEST", 1)) is True

    journal = _run(db.interroger("SELECT * FROM journaux WHERE category = 'intrigue'"))
    assert len(journal) == 1
    donnees = json.loads(journal[0]["data_json"])
    assert donnees["type"] == "choix_auteur"
    assert donnees["code"] == "incoherence_confirmee"
    assert journal[0]["entity_name"] == "Aria"


def test_numero_inconnu_ou_deja_valide_refuse(dossier_donnees):
    _initialiser()
    from app.services import alertes

    assert _run(alertes.valider_choix_auteur("P-TEST", 99)) is False
    _run(alertes.creer("P-TEST", _alerte()))
    assert _run(alertes.valider_choix_auteur("P-TEST", 1)) is True
    assert _run(alertes.valider_choix_auteur("P-TEST", 1)) is False  # déjà validée


def test_barriere_1_exclusions_validees_pour_prompt(dossier_donnees):
    db = _initialiser()
    from app.services import alertes

    _run(alertes.creer("P-TEST", _alerte()))
    _run(alertes.creer("P-TEST", _alerte(code="incoherence_potentielle", niveau="information", cible="Kael", motif="Autre")))
    _run(alertes.valider_choix_auteur("P-TEST", 1))

    exclus = _run(alertes.exclusions_validees("P-TEST"))
    assert exclus == [{"code": "incoherence_confirmee", "cible": "Aria"}]


def test_barriere_2_post_filtre_python():
    from app.services.alertes import filtrer_redetections

    validees = [{"code": "incoherence_confirmee", "cible": "Aria"}]
    detectees = [
        AlerteDetectee(code="incoherence_confirmee", niveau="avertissement", cible="Aria", motif="Re-détectée"),  # écartée
        AlerteDetectee(code="incoherence_potentielle", niveau="information", cible="Aria", motif="Code différent"),  # conservée
        AlerteDetectee(code="incoherence_confirmee", niveau="avertissement", cible="Kael", motif="Cible différente"),  # conservée
    ]
    restantes = filtrer_redetections(detectees, validees)
    assert [a.motif for a in restantes] == ["Code différent", "Cible différente"]