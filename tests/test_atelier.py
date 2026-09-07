"""Tests d'intégration de l'atelier E5 (J2.5) : boutons de workflow (validation
réservée aux chapitres, « Soumettre un autre texte »), validation du TEXTE
AFFICHÉ + backup, nouvelle version (redirection vers le bon id), choix de
Forme, alternatives, embellissement + réévaluation, pré-remplissage de E3."""

import asyncio
import hashlib
import json
import time
from pathlib import Path

from app.config import settings
from app.llm.mock import MockLLM
from app.services import analyse as service_analyse

TEXTE = "Les cavaliers part à l'aube vers la cité."
COURANT = "Les cavaliers partent à l'aube vers la cité."

REPONSE_FORME = json.dumps(
    {
        "corrections": [
            {
                "id": "c-0001", "phase": "forme", "type": "accord_sujet_verbe",
                "paragraphe_id": "p-1", "debut": 14, "fin": 18,
                "contexte_avant": "Les cavaliers ", "original": "part",
                "correction": "partent", "explication": "Accord.",
                "regle": "Accord sujet-verbe", "variantes": [],
            }
        ]
    },
    ensure_ascii=False,
)


def _modeles_distincts(monkeypatch):
    for champ, valeur in [
        ("modele_phase2", "m-p2"),
        ("modele_forme", "m-forme"),
        ("modele_style", "m-style"),
        ("modele_technique", "m-technique"),
        ("modele_embellissement", "m-embellissement"),
    ]:
        monkeypatch.setattr(settings, champ, valeur)


def _attendre(client, identifiant, delai=10):
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


def _chapitre_termine(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={"m-forme": REPONSE_FORME})
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)
    identifiant = _lancer(client, {
        "texte": TEXTE, "categorie": "chapitre", "numero_chapitre": "1",
    })
    assert _attendre(client, identifiant) == "terminee"
    return identifiant


def test_bouton_valider_reserve_aux_chapitres(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)
    page = client.get(f"/analyses/{identifiant}")
    assert "Valider la version actuelle" in page.text

    identifiant_extrait = _lancer(client, {"texte": "Un extrait libre.", "categorie": "extrait"})
    assert _attendre(client, identifiant_extrait) == "terminee"
    page_extrait = client.get(f"/analyses/{identifiant_extrait}")
    assert "Soumettre un autre texte" in page_extrait.text
    assert "Valider la version actuelle" not in page_extrait.text


def test_valider_refuse_les_non_chapitres(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM()
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)
    identifiant = _lancer(client, {"texte": TEXTE, "categorie": "passage"})
    assert _attendre(client, identifiant) == "terminee"
    assert client.post(f"/analyses/{identifiant}/valider").status_code == 400


def test_valider_enregistre_le_texte_affiche_avec_backup(client, monkeypatch, dossier_donnees):
    identifiant = _chapitre_termine(client, monkeypatch)
    reponse = client.post(f"/analyses/{identifiant}/valider", follow_redirects=False)
    assert reponse.status_code == 303

    from app import db

    chapitres = asyncio.run(db.interroger("SELECT numero, texte, hash FROM chapitres"))
    assert len(chapitres) == 1
    assert chapitres[0]["texte"] == COURANT  # correction Forme APPLIQUÉE par défaut
    assert chapitres[0]["hash"] == hashlib.sha256(COURANT.encode("utf-8")).hexdigest()
    projets = asyncio.run(db.interroger("SELECT current_chapter_num FROM projets"))
    assert projets[0]["current_chapter_num"] == 1
    backups = list((dossier_donnees / "backups").glob("backup-*.sqlite3"))
    assert len(backups) == 1  # backup natif créé avant l'écriture narrative


def test_choix_original_puis_validation_enregistre_l_original(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)
    client.post(f"/analyses/{identifiant}/choix-forme",
                data={"correction_id": "c-0001", "decision": "original"})
    page = client.get(f"/analyses/{identifiant}")
    assert "refusee" in page.text  # marqué visuellement, non appliqué
    client.post(f"/analyses/{identifiant}/valider")

    from app import db

    chapitres = asyncio.run(db.interroger("SELECT texte FROM chapitres"))
    assert chapitres[0]["texte"] == TEXTE  # l'original restauré est bien enregistré


def test_nouvelle_version_redirige_vers_le_nouvel_id(client, monkeypatch):
    """Régression (piège J2.1) : la redirection doit pointer vers le NOUVEL id,
    jamais vers /analyses/1 (déballage rowcount au lieu de lastrowid)."""
    identifiant = _chapitre_termine(client, monkeypatch)
    reponse = client.post(f"/analyses/{identifiant}/nouvelle-version", follow_redirects=False)
    assert reponse.status_code == 303
    assert reponse.headers["location"] == "/analyses/2"
    from app import db

    lignes = asyncio.run(db.interroger("SELECT texte_source FROM analyses WHERE id = 2"))
    paragraphe = json.loads(lignes[0]["texte_source"])[0]
    assert paragraphe["runs"][0]["texte"] == COURANT  # le texte courant est repris
    assert _attendre(client, 2) == "terminee"


def test_alternative_appliquee_puis_validee(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)
    reponse = client.post(
        f"/analyses/{identifiant}/appliquer-alternative",
        data={"paragraphe_id": "p-1", "fragment": "partent",
              "contexte": "Les cavaliers ", "texte": "s'élancent"},
    )
    assert reponse.status_code == 200
    # NB (piège J2.4) : Jinja2 auto-échappe les apostrophes — ne jamais affirmer
    # sur une chaîne contenant « ' » dans du HTML rendu.
    assert "&#39;élancent" in reponse.text
    page = client.get(f"/analyses/{identifiant}")
    assert "&#39;élancent" in page.text
    # la Forme intersectée est obsolète (visible dans le JSON de la barre latérale,
    # `tojson` échappant les accents)
    assert '"etat": "obsolete"' in page.text
    client.post(f"/analyses/{identifiant}/valider")

    from app import db

    chapitres = asyncio.run(db.interroger("SELECT texte FROM chapitres"))
    assert chapitres[0]["texte"] == "Les cavaliers s'élancent à l'aube vers la cité."


def test_reevaluer_remplace_les_corrections_du_paragraphe(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={
        "m-forme": '{"corrections": []}',
        "m-style": json.dumps({
            "corrections": [{
                "id": "c-0009", "phase": "style", "type": "repetition",
                "paragraphe_id": "p-1", "debut": 0, "fin": 3,
                "contexte_avant": "", "original": "Les", "correction": "Les",
                "explication": "Test de réévaluation.", "regle": "", "variantes": [],
            }]
        }, ensure_ascii=False),
    })
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    reponse = client.post(f"/analyses/{identifiant}/reevaluer",
                          data={"paragraphe_id": "p-1"})
    assert reponse.status_code == 200
    assert "c-r0001" in reponse.text  # les nouvelles corrections remplacent les anciennes
    assert "c-0001" not in reponse.text  # l'ancienne correction Forme n'est plus là
    assert "partent" in reponse.text     # le texte courant est conservé


def test_api_embellir_et_application_avec_reevaluation(client, monkeypatch):
    identifiant = _chapitre_termine(client, monkeypatch)
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={
        "m-embellissement": '{"texte": "s\'élancent", "explication": "Élan."}',
        "m-forme": '{"corrections": []}',
        "m-style": '{"corrections": []}',
        "m-technique": '{"corrections": []}',
    })
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)

    suggestion = client.post("/api/embellir", json={
        "fragment": "partent",
        "paragraphe_texte": COURANT,
        "contexte": "",
    })
    assert suggestion.json() == {"texte": "s'élancent", "explication": "Élan."}

    reponse = client.post(
        f"/analyses/{identifiant}/appliquer-embellissement",
        data={"paragraphe_id": "p-1", "fragment": "partent",
              "contexte": "Les cavaliers ", "texte": "s'élancent"},
    )
    assert reponse.status_code == 200
    assert "&#39;élancent" in reponse.text  # auto-échappement Jinja2 (piège J2.4)
    assert "Élan." not in reponse.text  # le mock de réévaluation remet une liste vide
    page = client.get(f"/analyses/{identifiant}")
    assert "&#39;élancent" in page.text


def test_api_alternatives_retourne_les_suggestions(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM(reponses={
        "m-style": json.dumps(
            {"alternatives": ["s'élancent", "bondissent"], "explication": "Champ lexical du mouvement."},
            ensure_ascii=False,
        )
    })
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    reponse = client.post("/api/alternatives", json={
        "fragment": "partent", "paragraphe_texte": COURANT,
    })
    assert reponse.json()["alternatives"] == ["s'élancent", "bondissent"]


def test_prefill_dernieres_options_sur_e3(client, monkeypatch):
    _modeles_distincts(monkeypatch)
    mock = MockLLM()
    monkeypatch.setattr(service_analyse, "_client_llm", lambda: mock)
    client.post("/projets", data={"titre": "Mon roman"}, follow_redirects=True)
    identifiant = _lancer(client, {
        "texte": "Un extrait libre.", "categorie": "extrait",
        "phases": '{"forme": true, "style": false, "technique": false}',
    })
    assert _attendre(client, identifiant) == "terminee"

    page = client.get("/analyses/nouveau")
    assert 'value="extrait" checked' in page.text
    assert 'value="chapitre" checked' not in page.text
    assert 'id="case-technique" >' in page.text        # décochée (dernier choix mémorisé)
    assert 'id="case-style" checked' not in page.text


# --- Jalon A : menu contextuel fiable (rendu) ---------------------------------


def test_menu_contextuel_et_popover_masques_au_chargement(client, monkeypatch):
    """Jalon A (rendu) : le menu contextuel et le popover de suggestion sont
    rendus avec l'attribut `hidden` (masqués au chargement), et le CSS contient
    la garde `[hidden] { display: none !important }` — avant, la règle
    `.menu-contextuel { display: flex }` neutralisait le `hidden` (menu toujours
    visible). Position fixed + clientX/clientY, positionnement du popover,
    fermeture au clic extérieur et à Échap : comportement JS de `app.js`,
    à vérifier manuellement au navigateur (aucun moteur JS dans pytest)."""
    identifiant = _chapitre_termine(client, monkeypatch)
    page = client.get(f"/analyses/{identifiant}")
    assert '<div id="menu-contextuel" class="menu-contextuel" hidden>' in page.text
    assert '<div id="popover-action" class="bulle-contexte popover-atelier" hidden></div>' in page.text
    css = (Path(__file__).resolve().parents[1] / "app" / "static" / "style.css").read_text(
        encoding="utf-8"
    )
    assert "[hidden] { display: none !important; }" in css
    assert "position: fixed" in css