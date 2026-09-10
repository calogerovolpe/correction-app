"""Tests de la couche LLM — client compatible OpenAI (transport mocké), fail-fast,
mock scripté et pipeline complet extraction -> réconciliation -> déduplication."""

import asyncio
import json

import httpx
import pytest

from app.llm.client import ClientLLM, format_schema_strict
from app.llm.mock import MockLLM
from app.models import (
    Correction,
    ErreurTroncatureLLM,
    PannePhase,
    ReponseCorrections,
)
from app.services import reconciliation as reco
from app.services.normalisation import Paragraphe

P1 = Paragraphe(id="p-1", texte="Les cavaliers part à l'aube vers la cité.")


def _run(coro):
    return asyncio.run(coro)


def _transport(status=200, contenu='{"corrections": []}'):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            json={"choices": [{"message": {"content": contenu}, "finish_reason": "stop"}]},
        )

    return httpx.MockTransport(handler)


# --- Client réel (transport mocké httpx, cahier des charges §4.3) ------------


def test_client_completer_et_entetes_bearer():
    requetes = []

    def handler(request: httpx.Request) -> httpx.Response:
        requetes.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = ClientLLM(base_url="http://test/v1", api_key="cle-test", transport=httpx.MockTransport(handler))
    contenu = _run(client.completer("modele-x", [{"role": "user", "content": "ping"}]))
    assert contenu == "ok"
    assert requetes[0].headers["Authorization"] == "Bearer cle-test"
    assert json.loads(requetes[0].content)["model"] == "modele-x"


def test_client_ping_reussi():
    client = ClientLLM(base_url="http://test/v1", transport=_transport())
    assert _run(client.ping("m")) is True


def test_client_ping_echec_apres_nouvelles_tentatives():
    client = ClientLLM(base_url="http://test/v1", transport=_transport(status=500))
    assert _run(client.ping("m", retries=1)) is False  # 1 nouvelle tentative -> 2 essais


def test_fail_fast_parallele_liste_les_indisponibles():
    ok = ClientLLM(base_url="http://test/v1", transport=_transport())
    assert _run(ok.verifier_disponibilite({"forme": "m1", "style": "m2"})) == []
    ko = ClientLLM(base_url="http://test/v1", transport=_transport(status=503))
    assert _run(ko.verifier_disponibilite({"forme": "m1", "style": "m2"})) == ["forme", "style"]


# --- FA5 : Custom Structured Outputs et détection de troncature ----------------


def _client_capteur(requetes: list) -> ClientLLM:
    def handler(request: httpx.Request) -> httpx.Response:
        requetes.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    return ClientLLM(base_url="http://test/v1", transport=httpx.MockTransport(handler))


def test_format_schema_strict_genere_le_response_format_mistral():
    attendu = format_schema_strict(ReponseCorrections)
    assert attendu["type"] == "json_schema"
    interne = attendu["json_schema"]
    assert interne["name"] == "ReponseCorrections"
    assert interne["strict"] is True
    assert interne["schema"]["properties"]["corrections"]["type"] == "array"
    assert "Correction" in interne["schema"]["$defs"]


def test_completer_envoie_le_schema_strict_quand_fourni():
    requetes = []
    client = _client_capteur(requetes)
    _run(client.completer(
        "modele-x", [{"role": "user", "content": "analyse"}],
        schema_modele=ReponseCorrections,
    ))
    corps = json.loads(requetes[0].content)
    assert corps["response_format"]["type"] == "json_schema"
    assert corps["response_format"]["json_schema"]["strict"] is True
    assert corps["response_format"]["json_schema"]["name"] == "ReponseCorrections"


def test_completer_sans_schema_nenvoie_pas_de_response_format():
    requetes = []
    client = _client_capteur(requetes)
    _run(client.completer("modele-x", [{"role": "user", "content": "ping"}]))
    assert "response_format" not in json.loads(requetes[0].content)


def test_completer_leve_erreur_troncature_si_finish_reason_length():
    """FA5 — finish_reason='length' : le JSON arrive coupé, l'appel qui vérifie
    la troncature lève une exception explicite au lieu d'ingérer du partiel."""
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "choices": [{
                "message": {"content": '{"corrections": [{"id": "c-0'},  # JSON coupé
                "finish_reason": "length",
            }],
        })

    client = ClientLLM(base_url="http://test/v1", transport=httpx.MockTransport(handler))
    with pytest.raises(ErreurTroncatureLLM):
        _run(client.completer(
            "m", [], max_tokens=2048,
            schema_modele=ReponseCorrections, verifier_troncature=True,
        ))


def test_completer_tolere_un_finish_reason_stop():
    client = ClientLLM(base_url="http://test/v1", transport=_transport())
    assert _run(client.completer(
        "m", [], schema_modele=ReponseCorrections, verifier_troncature=True,
    )) == '{"corrections": []}'


def test_ping_ne_verifie_pas_la_troncature():
    """Le ping (max_tokens=5) arrive naturellement coupé : il ne doit PAS lever."""
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "choices": [{
                "message": {"content": "Pong ! Le serveur fonctionne"},
                "finish_reason": "length",
            }],
        })

    client = ClientLLM(base_url="http://test/v1", transport=httpx.MockTransport(handler))
    assert _run(client.ping("m", retries=0)) is True


# --- Mock LLM et panne -> Option B (v6 §8.5, §14.2) --------------------------


def test_mock_liste_vide_par_defaut():
    m = MockLLM()
    assert _run(m.completer("m", [])) == '{"corrections": []}'
    assert _run(m.verifier_disponibilite({"forme": "m"})) == []
    assert _run(MockLLM(ping_ok=False).verifier_disponibilite({"forme": "m"})) == ["forme"]


def test_panne_en_cours_danalyse_provoque_exception():
    m = MockLLM(panne_completer=True)
    with pytest.raises(RuntimeError):
        _run(m.completer("m", []))


def test_mock_troncature_leve_erreur_troncature():
    """FA5 : `troncature=True` simule un finish_reason='length' — le mock lève
    `ErreurTroncatureLLM` (le pipeline doit la convertir en PannePhase)."""
    m = MockLLM(troncature=True)
    with pytest.raises(ErreurTroncatureLLM):
        _run(m.completer("m", [], verifier_troncature=True))


def test_mock_accepte_les_parametres_schema_strict():
    m = MockLLM()
    sortie = _run(m.completer(
        "m", [], max_tokens=4096,
        schema_modele=ReponseCorrections, verifier_troncature=True,
    ))
    assert sortie == '{"corrections": []}'


def test_sortie_non_parsable_leve_panne_de_phase():
    m = MockLLM(reponses={"m": "Je ne peux pas répondre en JSON."})
    sortie = _run(m.completer("m", []))
    with pytest.raises(PannePhase):
        reco.extraire_corrections(sortie, "forme")


# --- Pipeline complet sur réponses scriptées (v6 §8.2-8.3, R1-b) -------------


def test_pipeline_complet_extraction_reconciliation():
    reponses = {
        "modele-style": json.dumps(
            {
                "corrections": [
                    {
                        "id": "c-0001", "phase": "style", "type": "repetition",
                        "paragraphe_id": "p-1", "debut": 14, "fin": 18,
                        "contexte_avant": "Les cavaliers ", "original": "part",
                        "correction": "s'élancent", "explication": "Répétition rapprochée.",
                        "regle": "Rythme", "variantes": ["bondissent"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        "modele-embellissement": json.dumps(
            {
                "corrections": [
                    {
                        "id": "c-0002", "phase": "embellissement", "type": "prosodie",
                        "paragraphe_id": "p-1", "debut": 14, "fin": 18,
                        "contexte_avant": "Les cavaliers ", "original": "part",
                        "correction": "s'envolent", "explication": "Assonance.",
                        "regle": "", "variantes": ["volent", "fendent l'air"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
    }
    m = MockLLM(reponses=reponses)
    paragraphes = {"p-1": P1}

    style = reco.extraire_corrections(_run(m.completer("modele-style", [])), "style")
    embellissement = reco.extraire_corrections(_run(m.completer("modele-embellissement", [])), "embellissement")
    toutes = style + embellissement
    assert len(toutes) == 2

    reconciliees = []
    for correction in toutes:
        resultat = reco.reconcilier(correction, paragraphes[correction.paragraphe_id])
        if resultat is not None:
            reconciliees.append(resultat)
    assert len(reconciliees) == 2

    conservees = reco.renumeroter(reconciliees)
    # Déduplication = règle d'affichage (R1-b) : recouvrement exact — les DEUX
    # coexistent, AUCUNE n'est absorbée (l'ancienne migration §8.4 est supprimée).
    assert [c.phase for c in conservees] == ["style", "embellissement"]
    assert [c.id for c in conservees] == ["c-0001", "c-0002"]


def test_temperatures_par_phase_respectees():
    m = MockLLM()
    _run(m.completer("m-forme", [], temperature=0.0))
    _run(m.completer("m-embellissement", [], temperature=0.8))
    assert m.appels == [("m-forme", 0.0), ("m-embellissement", 0.8)]