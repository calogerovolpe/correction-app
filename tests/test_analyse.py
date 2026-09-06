"""Tests d'intégration des analyses (jalon J2) — cahier des charges §4.4, §9-J2.

Le job tourne en tâche asynchrone sur la boucle du TestClient ; le polling se fait
par HTTP (jamais d'accès DB direct concurrent — verrou asyncio mono-boucle)."""

import asyncio
import json
import time

from app.config import settings
from app.llm.mock import MockLLM
from app.services import analyse as service_analyse

TEXTE = "Les cavaliers part à l'aube vers la cité."

REPONSE_FORME = json.dumps(
    {
        "corrections": [
            {
                "id": "c-0001", "phase": "forme", "type": "accord_sujet_verbe",
                "paragraphe_id": "p-1", "debut": 14, "fin": 18,
                "contexte_avant": "Les cavaliers ", "original": "part",
                "correction": "partent", "explication": "Le sujet pluriel commande l'accord.",
                "regle": "Accord sujet-verbe", "variantes": [],
            }
        ]
    },
    ensure_ascii=False,
)


REPONSE_EMBELLISSEMENT = json.dumps(
    {
        "corrections": [
            {
                "id": "c-0002", "phase": "embellissement", "type": "prosodie",
                "paragraphe_id": "p-2", "debut": 36, "fin": 40,
                "contexte_avant": "vers la ", "original": "cité",
                "correction": "cité endormie", "explication": "Assonance discrète.",
                "regle": "", "variantes": ["cité muette", "cité ensevelie"],
            }
        ]
    },
    ensure_ascii=False,
)


def _modeles_distincts(monkeypatch):
    """Modèles distincts par phase pour scripter le mock indépendamment."""
    for champ, valeur in [
        ("modele_phase2", "m-p2"),
        ("modele_forme", "m-forme"),
        ("modele_style", "m-style"),
        ("modele_technique", "m-technique"),
        ("modele_embellissement", "m-embellissement"),
    ]:
        monkeypatch.setattr(settings, champ, valeur)


def _attendre(client, identifiant, delai=10):
    """Polling HTTP jusqu'au statut final (terminee / echec / rejetee)."""
    limite = time.time() + delai
    while time.time() < limite:
        page = client.get(f"/analyses/{identifiant}")
        if "Résultat de l'analyse" in page.text:
            return "terminee"
        if "— échouée" in page.text:
            return "echec"
        if "— refusée" in page.text:
            return "rejetee"
        time.sleep(0.05)
    return "timeout"


def _lancer(client, donnees):
    reponse = client.post("/analyses", data=donnees, follow_redirects=False)
    assert reponse.status_code == 303
    return int(reponse.headers["location"].rsplit("/", 1)[-1])


def _projet_courant(dossier_donnees, courant, statut="ok"):
    """Projet pré-rempli AVANT le client (aucune boucle concurrente)."""
    from app import db

    db.init_db()
    asyncio.run(db.executer(
        "INSERT INTO projets (projet_id, titre, current_chapter_num, chain_status) "
        "VALUES ('P-TEST', 'Roman test', ?, ?)", (courant, statut)))
    asyncio.run(db.executer(
        "INSERT INTO parametres (cle, valeur) VALUES ('projet_actif', 'P-TEST')", ()))

def test_analyse_complete_extrait(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": REPONSE_FORME, "m-embellissement": '{"corrections": []}'})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)

    identifiant = _lancer(client, {"texte": TEXTE, "categorie": "auto"})
    assert _attendre(client, identifiant) == "terminee"

    page = client.get(f"/analyses/{identifiant}")
    assert "ins--forme" in page.text          # annotation colorée
    assert "partent" in page.text
    assert 'data-paragraphe-id="p-1"' in page.text
    assert "pastille--forme" in page.text     # légende interactive
    # Matrice Extrait : embellissement actif par défaut, style/technique non appelés
    appels = [modele for modele, _ in mock.appels]
    assert "m-forme" in appels and "m-embellissement" in appels
    assert "m-style" not in appels and "m-technique" not in appels


def test_chapitre_conforme_matrice_chapitre(client, monkeypatch, dossier_donnees):
    _modeles_distincts(monkeypatch)
    _projet_courant(dossier_donnees, 3)
    mock = MockLLM(reponses={
        "m-forme": REPONSE_FORME, "m-style": '{"corrections": []}',
        "m-technique": '{"corrections": []}',
    })
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)

    texte = "4 : La nuit tombe\n\nLes cavaliers part à l'aube vers la cité."
    identifiant = _lancer(client, {"texte": texte, "categorie": "auto"})
    assert _attendre(client, identifiant) == "terminee"

    page = client.get(f"/analyses/{identifiant}")
    assert "chapitre officiel conforme" in page.text
    appels = [modele for modele, _ in mock.appels]
    # Matrice Chapitre (v6 §5.4) : forme + style + technique, PAS d'embellissement
    assert "m-style" in appels and "m-technique" in appels
    assert "m-embellissement" not in appels
    assert "Lecture Embellissement" not in page.text  # bouton absent sans suggestions


def test_rupture_reclassement_en_extrait(client, monkeypatch, dossier_donnees):
    _modeles_distincts(monkeypatch)
    _projet_courant(dossier_donnees, 3)
    mock = MockLLM(reponses={"m-forme": '{"corrections": []}',
                            "m-embellissement": REPONSE_EMBELLISSEMENT})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)

    texte = "5 : Hors séquence\n\nLes cavaliers part à l'aube vers la cité."
    identifiant = _lancer(client, {"texte": texte, "categorie": "auto"})
    assert _attendre(client, identifiant) == "terminee"  # jamais bloquée (v6 §6.5)

    page = client.get(f"/analyses/{identifiant}")
    assert "hors séquence" in page.text        # bannière reclassement_extrait
    assert "traité comme Extrait" in page.text
    assert "Lecture Embellissement" in page.text  # bouton présent (suggestions actives en Extrait)


def test_fail_fast_rejetee_zero_token(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(ping_ok=False)
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)

    identifiant = _lancer(client, {"texte": TEXTE, "categorie": "auto"})
    assert _attendre(client, identifiant) == "rejetee"
    page = client.get(f"/analyses/{identifiant}")
    assert "ne répond pas" in page.text           # gabarit v6 §4.2
    assert mock.appels == []                       # zéro token d'analyse consommé


def test_panne_option_b_aucun_resultat_partiel(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(panne_completer=True)
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)

    identifiant = _lancer(client, {"texte": TEXTE, "categorie": "auto"})
    assert _attendre(client, identifiant) == "echec"
    page = client.get(f"/analyses/{identifiant}")
    assert "Exécution interrompue" in page.text     # gabarit Option B (v6 §14.2)
    assert "échoué en cours" in page.text
    assert "Résultat de l'analyse" not in page.text   # aucun résultat partiel


def test_sortie_non_parsable_panne_de_phase(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": "Je ne peux pas répondre en JSON.",
                             "m-embellissement": "Panne incompréhensible."})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)

    identifiant = _lancer(client, {"texte": TEXTE, "categorie": "auto"})
    assert _attendre(client, identifiant) == "echec"  # PannePhase -> Option B (v6 §8.5)


def test_remplacement_refuse_chapitre_jamais_soumis(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM()
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)

    identifiant = _lancer(client, {"texte": TEXTE, "categorie": "auto", "remplacement": "on"})
    assert _attendre(client, identifiant) == "rejetee"  # refus zéro token (v6 §6.6)
    page = client.get(f"/analyses/{identifiant}")
    assert "impossible de remplacer" in page.text  # session vierge : aucun chapitre officiel
    assert mock.appels == []


def test_garde_fou_taille_refus_explicite(client, monkeypatch):
    monkeypatch.setattr(settings, "max_caracteres", 50)
    client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)

    page = client.post("/analyses", data={"texte": "x" * 120, "categorie": "auto"})
    assert page.status_code == 400
    assert "la limite est de 50" in page.text   # refus explicite, pas de troncature (v6 §2.3)


def test_redirection_identifiant_incremental(client, monkeypatch):
    """Régression (bug remonté par l'auteur) : la redirection après soumission
    pointait systématiquement vers /analyses/1 (déballage inversé : rowcount
    au lieu de lastrowid) — invisible en base vierge, où id=1 était toujours correct."""
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": REPONSE_FORME, "m-embellissement": '{"corrections": []}'})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)

    id1 = _lancer(client, {"texte": TEXTE, "categorie": "auto"})
    assert _attendre(client, id1) == "terminee"
    id2 = _lancer(client, {"texte": "Un second texte distinct, sans rapport.", "categorie": "extrait"})
    assert id2 == 2  # le bug renvoyait toujours 1
    assert _attendre(client, id2) == "terminee"
    assert "Résultat de l'analyse" in client.get("/analyses/2").text


def test_derogation_matrice_phases_libres(client, monkeypatch, dossier_donnees):
    """Décision de l'auteur (J2) : la matrice ne fait que pré-cocher — l'utilisateur
    peut tout décocher sauf ce qu'il veut (ex. un Chapitre corrigé Forme + Embellissement)."""
    _modeles_distincts(monkeypatch)
    _projet_courant(dossier_donnees, 3)
    mock = MockLLM(reponses={"m-forme": REPONSE_FORME, "m-embellissement": '{"corrections": []}'})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)

    texte = "4 : La nuit tombe\n\nLes cavaliers part à l'aube vers la cité."
    identifiant = _lancer(client, {
        "texte": texte, "categorie": "auto",
        "phases": '{"forme": true, "style": false, "technique": false, "embellissement": true}',
    })
    assert _attendre(client, identifiant) == "terminee"
    appels = [modele for modele, _ in mock.appels]
    assert "m-forme" in appels and "m-embellissement" in appels   # choisis par l'utilisateur
    assert "m-style" not in appels and "m-technique" not in appels  # décochés : dérogation matrice


def test_aucune_phase_selectionnee_refusee(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM()
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)

    page = client.post("/analyses", data={
        "texte": TEXTE, "categorie": "extrait",
        "phases": '{"forme": false, "style": false, "technique": false, "embellissement": false}',
    })
    assert page.status_code == 400
    assert "au moins un type de correction" in page.text
    assert mock.appels == []  # rien n'a été consommé


def test_temperature_choisie_par_l_utilisateur(client, monkeypatch):
    """Jauge de créativité : la température de l'Embellissement vient du formulaire."""
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": '{"corrections": []}', "m-embellissement": '{"corrections": []}'})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)

    identifiant = _lancer(client, {
        "texte": TEXTE, "categorie": "extrait",
        "phases": '{"forme": true, "embellissement": true}',
        "temperature_embellissement": "1.3",
    })
    assert _attendre(client, identifiant) == "terminee"
    temperatures = {modele: temperature for modele, temperature in mock.appels}
    assert temperatures["m-embellissement"] == 1.3   # jauge utilisateur
    assert temperatures["m-forme"] == 0.0            # correction : toujours 0.0


def test_texte_sans_projet_refuse(client):
    page = client.post("/analyses", data={"texte": TEXTE, "categorie": "auto"})
    assert page.status_code == 400
    assert "Aucun projet actif" in page.text


def test_jobs_orphelins_recuperes_au_demarrage(dossier_donnees):
    """Un job en attente ne survit pas à un redémarrage : au démarrage suivant,
    il passe en `echec` explicite (jamais de statut fantôme, cahier §4.4)."""
    import asyncio

    from fastapi.testclient import TestClient

    from app import db
    from app.main import app

    db.init_db()
    asyncio.run(db.executer(
        "INSERT INTO projets (projet_id, titre) VALUES ('P-ORPH', 'Orphelin')", ()))
    asyncio.run(db.executer(
        "INSERT INTO analyses (projet_id, texte_source, statut) "
        "VALUES ('P-ORPH', 'Texte interrompu', 'en_cours')", ()))

    with TestClient(app):  # le cycle de vie démarre -> récupération
        lignes = asyncio.run(db.interroger(
            "SELECT statut, erreur FROM analyses WHERE projet_id = 'P-ORPH'"))
    assert lignes[0]["statut"] == "echec"
    assert "redémarrage" in lignes[0]["erreur"]
