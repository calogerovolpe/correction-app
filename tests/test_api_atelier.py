"""Tests d'intégration de l'API JSON /api/v1 — Atelier E5 (jalon F3).

Couvre le contrat du plan « F3 — Atelier E5 » : GET `/api/v1/analyses/{id}/atelier`
(document annoté, projection par onglet, compteurs par phase, lecture pure),
choix Forme (filtre R2), édition directe (UX4), alternatives, embellissement
avec réévaluation sans état partiel, réévaluation manuelle, nouvelle version,
validation officielle, suggestions à la demande — avec un MockLLM injecté.

Polling PAR HTTP uniquement (jamais d'accès DB concurrent pendant qu'un job
tourne — verrou SQLite mono-boucle) : même règle que tests/test_analyse.py.
"""

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


def _chapitre_termine(client, monkeypatch):
    """Chapitre analysé (1 correction Forme) et terminé — via l'API F2."""
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": REPONSE_FORME})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})
    soumission = _soumettre(
        client,
        {"texte": TEXTE, "categorie": "chapitre", "numero_chapitre": 1},
    )
    finale = _attendre(client, soumission["id"])
    assert finale["statut"] == "terminee"
    return soumission["id"]


def _rechercher_groupe(donnees, groupe):
    """Entrée de barre latérale portant le groupe donné."""
    return next(c for c in donnees["document"]["corrections_barre"] if c["groupe"] == groupe)


def _texte_affiche(donnees):
    """Reconstruit le texte AFFICHÉ depuis les segments (les `ins` des segments
    Forme remplacent les `del` — c'est la projection servie au navigateur)."""
    morceaux = []
    for p in donnees["document"]["paragraphes"]:
        for s in p["segments"]:
            morceaux.append(s["ins"] if s["type"] == "forme" else s["texte"])
    return "".join(morceaux)


# --- GET /api/v1/analyses/{id}/atelier : document annoté ----------------------


def test_atelier_payload_complet_et_lecture_pure(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)

    reponse = client.get(f"/api/v1/analyses/{identifiant}/atelier")
    assert reponse.status_code == 200
    donnees = reponse.json()
    assert donnees["id"] == identifiant
    assert donnees["categorie"] == "chapitre"
    assert donnees["onglet"] == "tout"
    assert donnees["est_chapitre"] is True
    assert donnees["a_embellissement"] is False
    assert donnees["nb_corrections"] == 1
    assert donnees["compteurs"] == {"forme": 1}
    # Le segment Forme : original barré (del) + correction insérée (ins)
    segments = donnees["document"]["paragraphes"][0]["segments"]
    formes = [s for s in segments if s["type"] == "forme"]
    assert len(formes) == 1
    assert formes[0]["del"] == "part"
    assert formes[0]["ins"] == "partent"
    assert formes[0]["groupe"].startswith("g-")
    # Barre latérale : détails de la correction
    barre = donnees["document"]["corrections_barre"]
    assert barre[0]["phase"] == "forme"
    assert barre[0]["decision"] == "corrige"

    # Lecture pure : un second appel ne modifie rien (jamais de statut fantôme)
    relu = client.get(f"/api/v1/analyses/{identifiant}/atelier").json()
    assert relu == donnees


def test_atelier_projection_par_onglet_forme_seule(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)
    reponse = client.get(
        f"/api/v1/analyses/{identifiant}/atelier", params={"onglet": "forme"}
    )
    donnees = reponse.json()
    assert donnees["onglet"] == "forme"
    # Projection Forme : la correction reste marquée (del/ins) dans la couche
    # Forme, sans AUCUN marquage Style/Technique ; le texte restitué est cohérent.
    segments = donnees["document"]["paragraphes"][0]["segments"]
    formes = [s for s in segments if s["type"] == "forme"]
    assert len(formes) == 1
    assert formes[0]["ins"] == "partent"
    assert "part" in _texte_affiche(donnees) or "partent" in _texte_affiche(donnees)
    assert not any(
        "mark-style" in s.get("classes", "") or "mark-technique" in s.get("classes", "")
        for s in segments
    )
    # Compteurs calculés sur l'état complet (indépendants de la projection)
    assert donnees["compteurs"] == {"forme": 1}


def test_atelier_404_et_non_terminee_400(client, monkeypatch):
    reponse = client.get("/api/v1/analyses/9999/atelier")
    assert reponse.status_code == 404
    assert reponse.json()["detail"] == "Analyse introuvable."

    _modeles_distincts(monkeypatch)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})
    soumission = _soumettre(client, {"texte": TEXTE, "categorie": "extrait"})
    reponse = client.get(f"/api/v1/analyses/{soumission['id']}/atelier")
    finale = _attendre(client, soumission["id"])
    if finale["statut"] != "terminee":
        assert reponse.status_code == 400
    else:
        assert reponse.status_code == 200


# --- Actions de l'atelier -----------------------------------------------------


def test_choix_forme_original_filtre_la_projection(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)
    atelier = client.get(f"/api/v1/analyses/{identifiant}/atelier").json()
    correction_id = atelier["document"]["corrections_barre"][0]["id"]

    reponse = client.post(
        f"/api/v1/analyses/{identifiant}/choix-forme",
        json={"correction_id": correction_id, "decision": "original"},
    )
    assert reponse.status_code == 200
    donnees = reponse.json()
    groupe = donnees["document"]["corrections_barre"][0]["groupe"]
    ctx = client.get(
        f"/api/v1/analyses/{identifiant}/atelier", params={"onglet": "tout"}
    ).json()
    barre = _rechercher_groupe(ctx, groupe)
    assert barre["decision"] == "original"
    # Dans « tout », la Forme refusée apparaît marquée `refusee` (non appliquée)
    classes = " ".join(
        s.get("classes", "") for s in ctx["document"]["paragraphes"][0]["segments"]
    )
    assert "refusee" in classes


def test_editer_paragraphe_remplace_le_texte_courant(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)
    nouvelle = "Les cavaliers partent doucement vers la cité."
    reponse = client.post(
        f"/api/v1/analyses/{identifiant}/editer",
        json={"paragraphe_id": "p-1", "texte": nouvelle},
    )
    assert reponse.status_code == 200
    donnees = reponse.json()
    texte_affiche = _texte_affiche(donnees)
    assert nouvelle in texte_affiche
    # L'édition est un patch : le paragraphe est marqué « modifié »
    assert donnees["document"]["paragraphes"][0]["edite"] is True

    # Édition vide : refus explicite
    reponse = client.post(
        f"/api/v1/analyses/{identifiant}/editer",
        json={"paragraphe_id": "p-1", "texte": ""},
    )
    assert reponse.status_code == 400


def test_appliquer_alternative_remplace_le_fragment(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)
    reponse = client.post(
        f"/api/v1/analyses/{identifiant}/appliquer-alternative",
        json={
            "paragraphe_id": "p-1",
            "fragment": "vers la cité",
            "texte": "vers la ville",
            "contexte": "",
        },
    )
    assert reponse.status_code == 200
    donnees = reponse.json()
    texte_affiche = _texte_affiche(donnees)
    assert "vers la ville" in texte_affiche


def test_editer_puis_reevaluer_sans_perte_de_texte(client, monkeypatch):
    """RÉGRESSION FA1 (audit post-F3), workflow complet via /api/v1 : édition
    directe du paragraphe PUIS réévaluation — le paragraphe réécrit n'est
    JAMAIS remplacé par la seule correction réévaluée (rebase + ancrage sûr)."""
    identifiant = _chapitre_termine(client, monkeypatch)
    nouveau = "Texte entièrement réécrit par l'auteur pour son chapitre."
    reponse = client.post(
        f"/api/v1/analyses/{identifiant}/editer",
        json={"paragraphe_id": "p-1", "texte": nouveau},
    )
    assert reponse.status_code == 200

    # La réévaluation retourne une correction Forme sur UN SEUL mot du texte réécrit
    mock = MockLLM(
        reponses={
            "m-forme": json.dumps(
                {
                    "corrections": [
                        {
                            "id": "c-r0001", "phase": "forme", "type": "amelioration",
                            "paragraphe_id": "p-1", "debut": 6, "fin": 17,
                            "contexte_avant": "Texte ", "original": "entièrement",
                            "correction": "totalement", "explication": "Nuance plus juste.",
                            "regle": "Lexique", "variantes": [],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        }
    )
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    reponse = client.post(
        f"/api/v1/analyses/{identifiant}/reevaluer",
        json={"paragraphe_id": "p-1"},
    )
    assert reponse.status_code == 200
    # Le paragraphe réécrit est CONSERVÉ intégralement, seule la correction s'applique
    assert _texte_affiche(reponse.json()) == (
        "Texte totalement réécrit par l'auteur pour son chapitre."
    )


def test_fa3_charger_corrections_supporte_le_format_liste_legacy(client, monkeypatch):
    """RÉGRESSION (bug constaté en production) : les analyses créées AVANT le
    jalon R1-b stockaient `corrections.data_json` en LISTE PLATE. Le dictionnaire
    par phase étant la norme depuis R1-b, un chargement naïf (`par_phase.values()`)
    levait `AttributeError: 'list' object has no attribute 'values'` → Erreur 500
    à l'ouverture de l'atelier. Le service doit accepter LES DEUX formats."""
    import asyncio
    import json as module_json

    from app import db

    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": REPONSE_FORME})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})
    soumission = _soumettre(
        client, {"texte": TEXTE, "categorie": "chapitre", "numero_chapitre": 1}
    )
    identifiant = soumission["id"]
    assert _attendre(client, identifiant)["statut"] == "terminee"

    # Réécrit `corrections.data_json` au format LEGACY (liste plate, J1–R1-a)
    par_phase = module_json.loads(
        asyncio.run(db.interroger(
            "SELECT data_json FROM corrections WHERE analyse_id = ?", (identifiant,)
        ))[0]["data_json"]
    )
    asyncio.run(db.executer(
        "UPDATE corrections SET data_json = ? WHERE analyse_id = ?",
        (module_json.dumps([c for l in par_phase.values() for c in l]), identifiant),
    ))

    reponse = client.get(f"/api/v1/analyses/{identifiant}/atelier")
    assert reponse.status_code == 200  # 500 AVANT le correctif FA3
    donnees = reponse.json()
    assert donnees["nb_corrections"] == 1
    assert donnees["document"]["corrections_barre"][0]["id"] == "c-0001"


def test_fa3_charger_corrections_supporte_le_format_dict_par_phase(client, monkeypatch):
    """Régression du format ACTUEL (R1-b) : le dict par phase continue d'être
    chargé normalement après l'introduction de la rétrocompatibilité."""
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": REPONSE_FORME})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/api/v1/projets", json={"titre": "Mon roman"})
    soumission = _soumettre(
        client, {"texte": TEXTE, "categorie": "chapitre", "numero_chapitre": 1}
    )
    identifiant = soumission["id"]
    assert _attendre(client, identifiant)["statut"] == "terminee"
    reponse = client.get(f"/api/v1/analyses/{identifiant}/atelier")
    assert reponse.status_code == 200
    assert reponse.json()["nb_corrections"] == 1


def test_appliquer_embellissement_aucun_etat_partiel(client, monkeypatch):
    """Embellissement : patch PUIS réévaluation. Si la réévaluation échoue
    (panne MockLLM), RIEN n'est appliqué — zéro état partiel."""
    identifiant = _chapitre_termine(client, monkeypatch)

    # 1) Échec de la réévaluation → le texte n'est pas modifié
    mock = MockLLM(reponses={}, panne_completer=True)
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    reponse = client.post(
        f"/api/v1/analyses/{identifiant}/appliquer-embellissement",
        json={
            "paragraphe_id": "p-1",
            "fragment": "à l'aube",
            "texte": "au petit matin",
            "contexte": "",
        },
    )
    assert reponse.status_code == 400
    assert "n'a pas été modifié" in reponse.json()["detail"]
    etat = client.get(f"/api/v1/analyses/{identifiant}/atelier").json()
    assert "au petit matin" not in json.dumps(etat, ensure_ascii=False)

    # 2) Réévaluation OK → le patch est appliqué
    mock = MockLLM(reponses={})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    reponse = client.post(
        f"/api/v1/analyses/{identifiant}/appliquer-embellissement",
        json={
            "paragraphe_id": "p-1",
            "fragment": "à l'aube",
            "texte": "au petit matin",
            "contexte": "",
        },
    )
    assert reponse.status_code == 200
    etat = client.get(f"/api/v1/analyses/{identifiant}/atelier").json()
    assert "au petit matin" in json.dumps(etat, ensure_ascii=False)


def test_reevaluer_remplace_les_corrections_du_paragraphe(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)
    mock = MockLLM(
        reponses={
            "m-forme": json.dumps(
                {
                    "corrections": [
                        {
                            "id": "c-r0001", "phase": "forme", "type": "amelioration",
                            "paragraphe_id": "p-1", "debut": 19, "fin": 22,
                            "contexte_avant": "vers ", "original": "cité",
                            "correction": "ville", "explication": "Variante du contexte.",
                            "regle": "Choix de vocabulaire", "variantes": [],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        }
    )
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    reponse = client.post(
        f"/api/v1/analyses/{identifiant}/reevaluer",
        json={"paragraphe_id": "p-1"},
    )
    assert reponse.status_code == 200
    donnees = reponse.json()
    ids = [c["id"] for c in donnees["document"]["corrections_barre"]]
    # FA2 — identité documentaire : suite CONTINUE (après c-0001, le nouvel id
    # est c-r0002 — jamais c-r0001 recyclé, le compteur n'est pas remis à zéro).
    assert "c-r0002" in ids  # la correction réévaluée remplace l'ancienne


def test_suggestions_embellir_et_alternatives_a_la_demande(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(
        reponses={
            "m-embellissement": json.dumps(
                {"texte": "L'aube grise s'étirait sur la ville.", "explication": "Atmosphère."},
                ensure_ascii=False,
            ),
            "m-style": json.dumps(
                {"alternatives": ["ville", "agglomération", "cité"], "explication": ""},
                ensure_ascii=False,
            ),
        }
    )
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)

    reponse = client.post(
        "/api/v1/embellir",
        json={"fragment": "vers la cité", "paragraphe_texte": TEXTE, "contexte": ""},
    )
    assert reponse.status_code == 200
    assert "L'aube grise" in reponse.json()["texte"]

    reponse = client.post(
        "/api/v1/alternatives",
        json={"fragment": "part", "paragraphe_texte": TEXTE, "contexte": ""},
    )
    assert reponse.status_code == 200
    assert reponse.json()["alternatives"] == ["ville", "agglomération", "cité"]

    # Fragment vide : message explicite, aucun appel LLM
    mock.appels.clear()
    reponse = client.post(
        "/api/v1/embellir",
        json={"fragment": "   ", "paragraphe_texte": TEXTE, "contexte": ""},
    )
    assert reponse.status_code == 200
    assert reponse.json()["erreur"]
    assert mock.appels == []


# --- Workflow de fin de chapitre ----------------------------------------------


def test_nouvelle_version_relance_une_analyse(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)
    reponse = client.post(f"/api/v1/analyses/{identifiant}/nouvelle-version")
    assert reponse.status_code == 200
    nouvel_id = reponse.json()["nouvel_id"]
    assert nouvel_id != identifiant
    finale = _attendre(client, nouvel_id)
    assert finale["statut"] == "terminee"


def test_valider_chapitre_officiel_et_refus_extrait(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)
    reponse = client.post(f"/api/v1/analyses/{identifiant}/valider")
    assert reponse.status_code == 200
    resum = reponse.json()
    assert resum["ok"] is True
    assert resum["numero"] == 1
    assert resum["titre"] == "Chapitre 1"
    assert len(resum["hash"]) == 64  # SHA-256

    # Un Extrait ne peut pas être validé officiellement (400 explicite)
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    soumission = _soumettre(client, {"texte": "Un extrait libre.", "categorie": "extrait"})
    finale = _attendre(client, soumission["id"])
    assert finale["statut"] == "terminee"
    reponse = client.post(f"/api/v1/analyses/{soumission['id']}/valider")
    assert reponse.status_code == 400
    assert "Seul un Chapitre" in reponse.json()["detail"]