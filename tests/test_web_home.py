"""Tests de l'écran E1 — Accueil / Projets (version J0 minimale)."""


def test_accueil_vide(client):
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "Aucun projet" in reponse.text


def test_creation_de_projet(client):
    reponse = client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)
    assert reponse.status_code == 200
    assert "Mon roman" in reponse.text


def test_premier_projet_devient_actif(client):
    client.post("/projets", data={"titre": "Premier roman"}, follow_redirects=True)
    client.post("/projets", data={"titre": "Second roman"}, follow_redirects=True)
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "(actif)" in reponse.text
    # Un seul projet actif : le premier créé (v6 §6.3)
    assert reponse.text.count("(actif)") == 1


def test_titre_vide_refuse(client):
    reponse = client.post("/projets", data={"titre": "   "}, follow_redirects=True)
    assert reponse.status_code == 200
    assert "Aucun projet" in reponse.text


def test_page_projet_affiche_chain_status(client):
    client.post("/projets", data={"titre": "Roman chaîne"}, follow_redirects=True)
    reponse = client.get("/")
    assert "chaîne : vierge" in reponse.text
