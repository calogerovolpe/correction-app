"""Tests d'intégration de l'API JSON /api/v1 — Soumission E3 + suivi E4 (jalon F2).

Couvre le contrat du plan « F2 — Soumission E3 + suivi E4 » : préparation de E3
(GET /api/v1/soumission), soumission (POST /api/v1/analyses, refus explicites
400, mémoire des configurations), suivi (GET /api/v1/analyses/{id} : statuts
explicites, fail-fast / Option B visibles, synthèse `resultat`), avec un
MockLLM injecté — aucun appel à la vraie API Mistral. Le pipeline LLM n'est
pas modifié : on vérifie seulement le contrat HTTP.

Polling PAR HTTP uniquement (jamais d'accès DB concurrent pendant qu'un job
tourne — verrou SQLite mono-boucle) : même règle que tests/test_analyse.py.
"""

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
    """Polling HTTP du statut jusqu'à l'état final (terminee / echec / rejetee)."""
    limite = time.time() + delai
    while time.time() < limite:
        donnees = client.get(f"/api/v1/analyses/{identifiant}").json()
        if donnees["statut"] in ("terminee", "echec", "rejetee"):
            return donnees
        time.sleep(0.05)
    raise AssertionError("timeout — aucun statut final")


def _soumettre(client, payload):
    reponse = client.post("/api/v1/analyses", json=payload)
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def _projet_courant(dossier_donnees, courant, statut="ok"):
    """Projet pré-rempli AVANT le client (aucune boucle concurrente)."""
    from app import db

    db.init_db()
    asyncio.run(db.executer(
        "INSERT INTO projets (projet_id, titre, current_chapter_num, chain_status) "
        "VALUES ('P-TEST', 'Roman test', ?, ?)", (courant, statut)))
    asyncio.run(db.executer(
        "INSERT INTO parametres (cle, valeur) VALUES ('projet_actif', 'P-TEST')", ()))


# --- Préparation de E3 (GET /api/v1/soumission) ---------------------------------------


def test_preparer_soumission_sans_projet(client):
    reponse = client.get("/api/v1/soumission")
    assert reponse.status_code == 200
    donnees = reponse.json()
    assert donnees["projet"] is None
    assert donnees["numero_attendu"] == 0  # projet vierge : Prologue
    assert donnees["prefil"]["categorie"] == "chapitre"
    assert donnees["prefil"]["phases"] == {"forme": True, "style": True, "technique": True}
    assert donnees["max_caracteres"] == settings.max_caracteres


def test_preparer_soumission_numero_n_plus_un(client, dossier_donnees):
    _projet_courant(dossier_donnees, 3)
    donnees = client.get("/api/v1/soumission").json()
    assert donnees["projet"]["projet_id"] == "P-TEST"
    assert donnees["projet"]["chain_status"] == "ok"
    assert donnees["numero_attendu"] == 4  # N+1 pré-rempli
    assert donnees["max_caracteres"] >= 1
def test_memoire_dernieres_options_relue_apres_soumission(client, dossier_donnees, monkeypatch):
    """J2.5 : une soumission mémorise catégorie + phases, E3 les re-propose."""
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": REPONSE_FORME, "m-style": '{"corrections": []}'})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})

    _soumettre(client, {"texte": TEXTE, "categorie": "extrait"})
    donnees = client.get("/api/v1/soumission").json()
    assert donnees["prefil"]["categorie"] == "extrait"
    assert donnees["prefil"]["phases"] == {"forme": True, "style": True, "technique": False}


# --- Soumission (POST /api/v1/analyses) -------------------------------------------------


def test_soumission_extrait_terminee_et_synthese_resultat(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": REPONSE_FORME, "m-style": '{"corrections": []}'})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})

    soumission = _soumettre(client, {"texte": TEXTE, "categorie": "extrait"})
    assert soumission["statut"] == "en_attente"
    assert soumission["erreur"] is None
    assert soumission["resultat"] is None  # résultat seulement une fois terminée

    finale = _attendre(client, soumission["id"])
    assert finale["statut"] == "terminee"
    assert finale["resultat"] is not None
    assert finale["resultat"]["nb_corrections"] == 1
    assert finale["resultat"]["par_phase"] == {"forme": 1}  # style renvoie une liste vide

    appels = [modele for modele, _ in mock.appels]
    # Matrice Extrait : Forme + Style, PAS de Technique (J2.5)
    assert "m-forme" in appels and "m-style" in appels
    assert "m-technique" not in appels and "m-embellissement" not in appels


def test_soumission_chapitre_matrice_complete_et_numero_stocke(client, dossier_donnees, monkeypatch):
    _modeles_distincts(monkeypatch)
    _projet_courant(dossier_donnees, 3)
    mock = MockLLM(reponses={
        "m-forme": REPONSE_FORME, "m-style": '{"corrections": []}',
        "m-technique": '{"corrections": []}',
    })
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)

    soumission = _soumettre(client, {
        "texte": TEXTE, "categorie": "chapitre", "numero_chapitre": 4, "avec_codex": True,
    })
    finale = _attendre(client, soumission["id"])
    assert finale["statut"] == "terminee"
    assert finale["categorie"] == "chapitre"

    appels = [modele for modele, _ in mock.appels]
    # Matrice Chapitre : Forme + Style + Technique (pas d'Embellissement)
    assert {"m-forme", "m-style", "m-technique"} <= set(appels)
    assert "m-embellissement" not in appels

    from app import db
    lignes = asyncio.run(db.interroger(
        "SELECT options_json FROM analyses WHERE id = ?", (soumission["id"],)))
    options = json.loads(lignes[0]["options_json"])
    assert options["numero_chapitre"] == 4.0
    assert options["avec_codex"] is True
    assert options["forme"] is None  # phases absentes → pré-sélection par catégorie


def test_derogation_matrice_phases_libres(client, dossier_donnees, monkeypatch):
    """Décision J2.1 : la matrice ne fait que pré-cocher — on peut décocher
    (un Passage corrigé Forme seule)."""
    _modeles_distincts(monkeypatch)
    _projet_courant(dossier_donnees, 3)
    mock = MockLLM(reponses={"m-forme": REPONSE_FORME})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)

    soumission = _soumettre(client, {
        "texte": TEXTE, "categorie": "passage",
        "phases": {"forme": True, "style": False, "technique": False},
    })
    finale = _attendre(client, soumission["id"])
    assert finale["statut"] == "terminee"
    appels = [modele for modele, _ in mock.appels]
    assert "m-forme" in appels
    assert "m-style" not in appels and "m-technique" not in appels
def test_categorie_inconnue_repli_chapitre(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": "{\"corrections\": []}"})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})

    soumission = _soumettre(client, {"texte": TEXTE, "categorie": "auto"})
    finale = _attendre(client, soumission["id"])
    assert finale["statut"] == "terminee"
    assert finale["categorie"] == "chapitre"  # repli du routeur


def test_avec_codex_ignore_hors_chapitre(client, dossier_donnees, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": "{\"corrections\": []}", "m-style": "{\"corrections\": []}"})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    _projet_courant(dossier_donnees, 3)

    soumission = _soumettre(client, {
        "texte": TEXTE, "categorie": "extrait", "avec_codex": True,
    })
    _attendre(client, soumission["id"])

    from app import db
    lignes = asyncio.run(db.interroger(
        "SELECT options_json FROM analyses WHERE id = ?", (soumission["id"],)))
    options = json.loads(lignes[0]["options_json"])
    assert options["avec_codex"] is False  # réservé aux Chapitres


def test_ids_incrementaux_deux_soumissions(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": "{\"corrections\": []}", "m-style": "{\"corrections\": []}"})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})

    premier = _soumettre(client, {"texte": TEXTE, "categorie": "extrait"})
    second = _soumettre(client, {"texte": "Un second texte distinct, sans rapport.", "categorie": "extrait"})
    assert second["id"] != premier["id"]
    assert second["id"] == premier["id"] + 1  # incrément réel, pas un id figé

    assert _attendre(client, premier["id"])["statut"] == "terminee"
    assert _attendre(client, second["id"])["statut"] == "terminee"
# --- Refus explicites (400) --------------------------------------------------------------


def test_texte_vide_refuse(client):
    client.post("/api/v1/projets", json={"titre": "Mon roman"})
    reponse = client.post("/api/v1/analyses", json={"texte": "   ", "categorie": "extrait"})
    assert reponse.status_code == 400
    assert reponse.json()["detail"] == "Le texte soumis est vide."


def test_texte_trop_long_refus_explicite_sans_troncature(client, monkeypatch):
    monkeypatch.setattr(settings, "max_caracteres", 50)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})
    reponse = client.post("/api/v1/analyses", json={"texte": "x" * 120, "categorie": "extrait"})
    assert reponse.status_code == 400
    assert "la limite est de 50" in reponse.json()["detail"]
    assert "aucune troncature" in reponse.json()["detail"]


def test_aucun_projet_actif_refuse(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM()
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    reponse = client.post("/api/v1/analyses", json={"texte": TEXTE, "categorie": "extrait"})
    assert reponse.status_code == 400
    assert "Aucun projet actif" in reponse.json()["detail"]
    assert mock.appels == []  # zéro token consommé


def test_aucune_phase_selectionnee_refuse(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM()
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})
    reponse = client.post("/api/v1/analyses", json={
        "texte": TEXTE, "categorie": "extrait",
        "phases": {"forme": False, "style": False, "technique": False},
    })
    assert reponse.status_code == 400
    assert "au moins un type de correction" in reponse.json()["detail"]
    assert mock.appels == []


# --- Suivi E4 : statuts explicites, fail-fast visible -----------------------------------


def test_fail_fast_rejetee_visible_zero_token(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(ping_ok=False)
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})

    soumission = _soumettre(client, {"texte": TEXTE, "categorie": "chapitre"})
    finale = _attendre(client, soumission["id"])
    assert finale["statut"] == "rejetee"
    assert "ne répond pas" in finale["erreur"]  # gabarit fail-fast (v6 §4)
    assert finale["resultat"] is None
    assert mock.appels == []  # zéro token d'analyse consommé


def test_panne_option_b_echec_aucun_resultat_partiel(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(panne_completer=True)
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})

    soumission = _soumettre(client, {"texte": TEXTE, "categorie": "chapitre"})
    finale = _attendre(client, soumission["id"])
    assert finale["statut"] == "echec"
    assert "Exécution interrompue" in finale["erreur"]  # gabarit Option B (v6 §14.2)
    assert finale["resultat"] is None  # aucun résultat partiel


def test_statut_analyse_lecture_pure_ne_change_rien(client, dossier_donnees):
    """GET /api/v1/analyses/{id} est une LECTURE : il ne doit ni déclencher
    l'analyse ni modifier son état (jamais de statut fantôme)."""
    from app import db

    db.init_db()
    asyncio.run(db.executer(
        "INSERT INTO projets (projet_id, titre) VALUES ('P-TEST', 'Roman test')", ()))
    asyncio.run(db.executer(
        "INSERT INTO parametres (cle, valeur) VALUES ('projet_actif', 'P-TEST')", ()))
    asyncio.run(db.executer(
        "INSERT INTO analyses (projet_id, texte_source, statut, etape) "
        "VALUES ('P-TEST', ?, 'en_cours', 'normalisation')", (TEXTE,)))

    donnees = client.get("/api/v1/analyses/1").json()
    assert donnees["statut"] == "en_cours"
    assert donnees["etape"] == "normalisation"

    relu = client.get("/api/v1/analyses/1").json()
    assert relu["statut"] == "en_cours"  # inchangé


def test_analyse_inconnue_404(client):
    reponse = client.get("/api/v1/analyses/9999")
    assert reponse.status_code == 404
    assert reponse.json()["detail"] == "Analyse introuvable."


# --- FA6 : catalogue des modèles texte + modèle choisi à la soumission ---------


def test_preparer_soumission_expose_le_catalogue_de_modeles(client, dossier_donnees):
    """FA6 : E3 reçoit le catalogue des modèles texte Mistral (avec badge et
    description pour l'UI), le modèle par défaut (configuration Forme) et le
    dernier choix valide mémorisé (None au départ)."""
    _projet_courant(dossier_donnees, 3)
    donnees = client.get("/api/v1/soumission").json()
    ids = [m["id"] for m in donnees["modeles"]]
    assert "mistral-small-latest" in ids
    assert "mistral-large-latest" in ids
    assert "open-mistral-nemo" in ids
    assert "ministral-8b-latest" in ids
    recommande = next(m for m in donnees["modeles"] if m["badge"] == "Recommandé")
    assert recommande["id"] == "mistral-small-latest"
    assert recommande["libelle"] and recommande["description"]
    assert donnees["modele_defaut"]
    assert donnees["modele_memorise"] is None  # aucun choix encore mémorisé


def test_soumission_avec_modele_choisi_utilise_pour_toutes_les_phases(
    client, monkeypatch, dossier_donnees
):
    """FA6 : le modèle choisi à la soumission s'applique à TOUTES les phases
    de l'analyse (surcharge la configuration .env) et est mémorisé côté serveur."""
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": REPONSE_FORME})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})

    soumission = _soumettre(
        client,
        {"texte": TEXTE, "categorie": "extrait", "modele": "mistral-large-latest"},
    )
    finale = _attendre(client, soumission["id"])
    assert finale["statut"] == "terminee"
    appels = [modele for modele, _ in mock.appels]
    assert appels  # les phases actives ont tourné
    assert set(appels) == {"mistral-large-latest"}  # IA choisie pour toutes

    donnees = client.get("/api/v1/soumission").json()
    assert donnees["modele_memorise"] == "mistral-large-latest"


def test_soumission_modele_inconnu_repli_transparent_sur_configuration(
    client, monkeypatch
):
    """FA6 : un modèle hors catalogue est ignoré — la configuration `.env` par
    phase reste maîtresse (repli transparent, jamais de blocage)."""
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": REPONSE_FORME, "m-style": '{"corrections": []}'})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})

    soumission = _soumettre(
        client,
        {"texte": TEXTE, "categorie": "extrait", "modele": "modele-fantome"},
    )
    finale = _attendre(client, soumission["id"])
    assert finale["statut"] == "terminee"
    appels = [modele for modele, _ in mock.appels]
    assert set(appels) == {"m-forme", "m-style"}  # configuration par phase

    donnees = client.get("/api/v1/soumission").json()
    assert donnees["modele_memorise"] is None  # rien de mémorisé