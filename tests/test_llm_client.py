"""Tests de la couche LLM — client compatible OpenAI (transport mocké), fail-fast,
mock scripté et pipeline complet extraction -> réconciliation -> déduplication."""

import asyncio
import json

import httpx
import pytest

from app.llm.client import ClientLLM
from app.llm.mock import MockLLM
from app.models import PannePhase
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


def test_sortie_non_parsable_leve_panne_de_phase():
    m = MockLLM(reponses={"m": "Je ne peux pas répondre en JSON."})
    sortie = _run(m.completer("m", []))
    with pytest.raises(PannePhase):
        reco.extraire_corrections(sortie, "forme")


# --- Pipeline complet sur réponses scriptées (v6 §8.2-8.4) -------------------


def test_pipeline_complet_extraction_reconciliation_deduplication():
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

    fusion = reco.dedupliquer(reconciliees)
    assert len(fusion) == 1  # recouvrement exact : Style prioritaire (v6 §8.4)
    assert fusion[0].correction.phase == "style"
    assert fusion[0].embellissement_migre.suggestion == "s'envolent"


def test_temperatures_par_phase_respectees():
    m = MockLLM()
    _run(m.completer("m-forme", [], temperature=0.0))
    _run(m.completer("m-embellissement", [], temperature=0.8))
    assert m.appels == [("m-forme", 0.0), ("m-embellissement", 0.8)]