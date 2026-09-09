"""Tests de l'API JSON /api/v1 — Accueil & projets (jalon F1).

Couvre le contrat du plan « F1 — Accueil & projets E1 » : liste, création,
activation (un seul projet actif), suppression (protégée pour le projet
actif, en cascade sinon) et analyses récentes. Aucun appel LLM : ces
endpoints réutilisent les services et le SQL existants.
"""

import asyncio

from app import db


def _creer(client, titre="Mon roman"):
    return client.post("/api/v1/projets", json={"titre": titre})


def test_liste_vide(client):
    reponse = client.get("/api/v1/projets")
    assert reponse.status_code == 200
    assert reponse.json() == {"projets": []}


def test_creation_projet_premier_actif(client):
    reponse = _creer(client)
    assert reponse.status_code == 201
    donnees = reponse.json()
    assert donnees["projet_id"].startswith("P-")
    assert donnees["titre"] == "Mon roman"
    assert donnees["actif"] is True  # premier projet → actif (spec §11 déc. 16)
    assert donnees["chain_status"] == "vierge"
    assert donnees["current_chapter_num"] is None
    assert donnees["last_chapter_title"] is None
    assert donnees["created_at"]


def test_titre_vide_refuse(client):
    # Espaces seuls : passe la validation Pydantic (longueur > 0) mais est
    # retiré par le strip côté routeur → 400 explicite.
    reponse = client.post("/api/v1/projets", json={"titre": "   "})
    assert reponse.status_code == 400
    # Chaîne vide : refusée dès la validation du schéma (422).
    reponse2 = client.post("/api/v1/projets", json={"titre": ""})
    assert reponse2.status_code == 422


def test_un_seul_projet_actif_et_activation(client):
    premier = _creer(client, "Premier roman").json()
    second = _creer(client, "Second roman").json()
    assert premier["actif"] is True
    assert second["actif"] is False

    reponse = client.post(f"/api/v1/projets/{second['projet_id']}/activer")
    assert reponse.status_code == 204

    projets = client.get("/api/v1/projets").json()["projets"]
    actifs = [p for p in projets if p["actif"]]
    assert len(actifs) == 1
    assert actifs[0]["projet_id"] == second["projet_id"]


def test_activation_projet_inconnu(client):
    reponse = client.post("/api/v1/projets/P-INCONNU/activer")
    assert reponse.status_code == 404


def test_suppression_projet_actif_refusee(client):
    projet = _creer(client).json()
    reponse = client.delete(f"/api/v1/projets/{projet['projet_id']}")
    assert reponse.status_code == 409
    # Le projet est toujours présent
    restants = client.get("/api/v1/projets").json()["projets"]
    assert len(restants) == 1


def test_suppression_projet_non_actif_ok(client):
    premier = _creer(client, "Premier roman").json()
    second = _creer(client, "Second roman").json()
    client.post(f"/api/v1/projets/{second['projet_id']}/activer")

    reponse = client.delete(f"/api/v1/projets/{premier['projet_id']}")
    assert reponse.status_code == 204

    restants = client.get("/api/v1/projets").json()["projets"]
    assert [p["projet_id"] for p in restants] == [second["projet_id"]]
    assert restants[0]["actif"] is True


def test_suppression_cascade_sur_les_analyses(client):
    premier = _creer(client, "Premier roman").json()
    asyncio.run(
        db.executer(
            "INSERT INTO analyses (projet_id, texte_source) VALUES (?, ?)",
            (premier["projet_id"], "Texte source"),
        )
    )
    second = _creer(client, "Second roman").json()
    client.post(f"/api/v1/projets/{second['projet_id']}/activer")
    client.delete(f"/api/v1/projets/{premier['projet_id']}")

    restantes = asyncio.run(db.interroger("SELECT COUNT(*) AS n FROM analyses"))
    assert restantes[0]["n"] == 0  # ON DELETE CASCADE appliqué


def test_suppression_projet_inconnu(client):
    reponse = client.delete("/api/v1/projets/P-INCONNU")
    assert reponse.status_code == 404


def test_derniere_analyse_terminee_exposee_par_projet(client):
    """FA2 — le bouton « Ouvrir » de l'accueil a besoin de savoir où mener :
    chaque projet expose l'id de sa dernière analyse TERMINÉE (l'atelier E5
    n'est accessible que pour une analyse terminee)."""
    projet = _creer(client).json()
    pid = projet["projet_id"]
    # Une analyse terminée, puis une analyse échouée PLUS RÉCENTE :
    # c'est la dernière terminée qui doit être exposée (pas la plus récente).
    asyncio.run(
        db.executer(
            "INSERT INTO analyses (projet_id, texte_source, statut, categorie) "
            "VALUES (?, 'Texte.', 'terminee', 'chapitre')",
            (pid,),
        )
    )
    asyncio.run(
        db.executer(
            "INSERT INTO analyses (projet_id, texte_source, statut) "
            "VALUES (?, 'Texte.', 'echec')",
            (pid,),
        )
    )
    liste = client.get("/api/v1/projets").json()["projets"]
    cible = next(p for p in liste if p["projet_id"] == pid)
    terminee = asyncio.run(
        db.interroger(
            "SELECT MAX(id) AS n FROM analyses WHERE projet_id = ? AND statut = 'terminee'",
            (pid,),
        )
    )[0]["n"]
    assert cible["derniere_analyse_id"] == terminee

    # Un projet sans analyse terminée → None (le bouton mène à la soumission)
    second = _creer(client, "Roman vierge").json()
    liste2 = client.get("/api/v1/projets").json()["projets"]
    vierge = next(p for p in liste2 if p["projet_id"] == second["projet_id"])
    assert vierge["derniere_analyse_id"] is None


def test_analyses_recentes_limite_a_dix(client):
    projet = _creer(client).json()
    for i in range(12):
        asyncio.run(
            db.executer(
                "INSERT INTO analyses (projet_id, texte_source, statut, categorie) "
                "VALUES (?, ?, 'terminee', 'chapitre')",
                (projet["projet_id"], f"Texte {i}. " + "x" * 100),
            )
        )
    reponse = client.get("/api/v1/analyses")
    assert reponse.status_code == 200
    liste = reponse.json()["analyses"]
    assert len(liste) == 10
    assert liste[0]["id"] > liste[-1]["id"]  # tri DESC
    assert liste[0]["statut"] == "terminee"
    assert liste[0]["categorie"] == "chapitre"
    assert len(liste[0]["extrait"]) <= 60  # extrait tronqué