"""Tests de réconciliation — v6 §8.3 et §8.5
(critères J1 : offsets décalés, rejets, liste vide jamais une panne, panne -> Option B)."""

import json

import pytest

from app.models import Correction, PannePhase
from app.services import reconciliation as reco
from app.services.normalisation import Paragraphe

P1 = Paragraphe(id="p-1", texte="Les cavaliers part à l'aube vers la cité.")


def _correction(**surcharges) -> Correction:
    base = {
        "id": "c-0001",
        "phase": "forme",
        "type": "accord_sujet_verbe",
        "paragraphe_id": "p-1",
        "debut": 14,
        "fin": 18,
        "contexte_avant": "Les cavaliers ",
        "original": "part",
        "correction": "partent",
        "explication": "Le sujet pluriel commande l'accord du verbe au pluriel.",
        "regle": "Accord sujet-verbe",
        "variantes": [],
    }
    base.update(surcharges)
    return Correction(**base)


# --- Nettoyage et validation (v6 §8.5) -------------------------------------


def test_nettoyage_fences_et_preambule():
    brut = 'Voici mon analyse :\n```json\n{"corrections": []}\n```'
    assert reco.nettoyer_sortie_llm(brut) == '{"corrections": []}'


def test_liste_vide_est_un_resultat_valide_jamais_une_panne():
    assert reco.extraire_corrections('{"corrections": []}', "forme") == []


def test_panne_json_non_parsable():
    with pytest.raises(PannePhase):
        reco.extraire_corrections("ceci n'est pas du json", "forme")


def test_panne_racine_non_conforme():
    with pytest.raises(PannePhase):
        reco.extraire_corrections('{"resultats": []}', "forme")


def test_panne_racine_liste_bare():
    with pytest.raises(PannePhase):
        reco.extraire_corrections('[{"id": "c-0001"}]', "forme")


def test_entree_invalide_rejetee_sans_arret():
    sortie = json.dumps(
        {
            "corrections": [
                {
                    "id": "c-0001", "phase": "forme", "type": "accord",
                    "paragraphe_id": "p-1", "debut": 14, "fin": 18,
                    "contexte_avant": "Les cavaliers ", "original": "part",
                    "correction": "partent", "explication": "Accord.",
                    "regle": "Accord sujet-verbe", "variantes": [],
                },
                {"id": "c-0002"},  # entrée incomplète -> rejetée individuellement
            ]
        }
    )
    validees = reco.extraire_corrections(sortie, "forme")
    assert len(validees) == 1
    assert validees[0].id == "c-0001"


def test_champ_inconnu_rejete_extra_forbid():
    entree = json.dumps(
        {
            "corrections": [
                {
                    "id": "c-0001", "phase": "forme", "type": "accord",
                    "paragraphe_id": "p-1", "debut": 14, "fin": 18,
                    "contexte_avant": "", "original": "part", "correction": "partent",
                    "explication": "Accord.", "champ_inconnu": "interdit",
                }
            ]
        }
    )
    assert reco.extraire_corrections(entree, "forme") == []


def test_phase_forcee_si_libelle_errone():
    sortie = json.dumps(
        {
            "corrections": [
                {
                    "id": "c-0001", "phase": "style", "type": "accord",
                    "paragraphe_id": "p-1", "debut": 14, "fin": 18,
                    "contexte_avant": "", "original": "part", "correction": "partent",
                    "explication": "Accord.",
                }
            ]
        }
    )
    validees = reco.extraire_corrections(sortie, "forme")
    assert validees[0].phase == "forme"  # la phase est connue par construction


# --- Réconciliation des offsets (v6 §8.3) -----------------------------------


def test_invariant_exact_renvoie_telle_quelle():
    correction = reco.reconcilier(_correction(), P1)
    assert correction is not None
    assert (correction.debut, correction.fin) == (14, 18)


def test_decalage_repare_par_ancre():
    correction = reco.reconcilier(_correction(debut=20, fin=24), P1)
    assert correction is not None
    assert (correction.debut, correction.fin) == (14, 18)
    assert P1.texte[correction.debut:correction.fin] == "part"


def test_occurrence_unique_reparee():
    correction = reco.reconcilier(
        _correction(debut=0, fin=4, contexte_avant="", original="cité", correction="cité"), P1
    )
    assert correction is not None
    assert P1.texte[correction.debut:correction.fin] == "cité"


def test_fragment_ambigu_sans_ancre_rejete():
    correction = reco.reconcilier(
        _correction(debut=0, fin=1, contexte_avant="", original="a", correction="à"), P1
    )
    assert correction is None  # « a » apparaît plusieurs fois, aucune ancre : rejet


def test_fragment_introuvable_rejete():
    correction = reco.reconcilier(
        _correction(debut=0, fin=6, contexte_avant="", original="xyzabc", correction="…"), P1
    )
    assert correction is None

# --- Déduplication = règle d'AFFICHAGE (R1-b) -------------------------------
# L'ancienne `dedupliquer()` (v6 §8.4 : Style prioritaire, Embellissement migré
# dans le tooltip du Style) est SUPPRIMÉE : en réconciliation, AUCUNE correction
# n'est absorbée — en cas de recouvrement (exact ou partiel), Style et
# Embellissement COEXISTENT (superposés dans « Tout », séparés par onglet).


def test_recouvrement_exact_style_et_embellissement_coexistent():
    """Recouvrement exact Style/Embellissement : les DEUX sont conservées et
    renumérotées — aucune migration, aucune absorption (l'ancienne règle
    « Style prioritaire » v6 §8.4 est supprimée, décision R1-b)."""
    style = _correction(
        id="c-0001", phase="style", type="repetition",
        correction="s'élancent", variantes=["bondissent"],
    )
    embellissement = _correction(
        id="c-0002", phase="embellissement", type="prosodie",
        correction="s'envolent", variantes=["volent", "fendent l'air"],
        explication="Assonance discrète.",
    )
    conservees = reco.renumeroter([style, embellissement])
    assert [(c.phase, c.id) for c in conservees] == [
        ("style", "c-0001"), ("embellissement", "c-0002"),
    ]
    assert conservees[1].correction == "s'envolent"  # rien n'a été absorbé
    assert conservees[1].variantes == ["volent", "fendent l'air"]


def test_embellissement_sans_style_hote_est_conserve():
    embellissement = _correction(id="c-0004", phase="embellissement", type="prosodie")
    conservees = reco.renumeroter([embellissement])
    assert [c.phase for c in conservees] == ["embellissement"]

# --- Ids globaux uniques (jalon A, décision 33) ------------------------------


def test_renumeroter_assigne_des_ids_globaux_uniques_et_deterministes():
    """Chaque phase LLM émet ses ids sans coordination (ex. c-0001 deux fois) :
    la réassignation produit une suite unique ET déterministe."""
    style = _correction(id="c-0007", phase="style", type="repetition")
    forme = _correction(id="c-0001", phase="forme", type="accord")
    entrees = [style, forme]
    fusion = reco.renumeroter(entrees)
    assert [c.id for c in fusion] == ["c-0001", "c-0002"]
    encore = reco.renumeroter(entrees)  # déterministe : même entrée → mêmes ids
    assert [c.id for c in encore] == ["c-0001", "c-0002"]


# --- Rejet des no-op Forme (jalon A, décision 34) ----------------------------


def test_no_op_forme_rejetee_les_autres_conservees():
    """« cous » barré pour réécrire « cous » (explication « aucune correction
    nécessaire ») : rejet individuel, sans arrêt, les autres restent."""
    sortie = json.dumps(
        {
            "corrections": [
                {
                    "id": "c-0001", "phase": "forme", "type": "accord",
                    "paragraphe_id": "p-1", "debut": 14, "fin": 18,
                    "contexte_avant": "Les cavaliers ", "original": "part",
                    "correction": "partent", "explication": "Accord.",
                },
                {
                    "id": "c-0002", "phase": "forme", "type": "orthographe",
                    "paragraphe_id": "p-1", "debut": 36, "fin": 40,
                    "contexte_avant": "vers la ", "original": "cous",
                    "correction": "cous",
                    "explication": "aucune correction nécessaire",
                },
            ]
        },
        ensure_ascii=False,
    )
    validees = reco.extraire_corrections(sortie, "forme")
    assert [c.id for c in validees] == ["c-0001"]


def test_no_op_forme_seule_liste_vide_jamais_une_panne():
    sortie = json.dumps(
        {
            "corrections": [
                {
                    "id": "c-0001", "phase": "forme", "type": "orthographe",
                    "paragraphe_id": "p-1", "debut": 36, "fin": 40,
                    "original": "cous", "correction": "cous",
                    "explication": "aucune correction nécessaire",
                }
            ]
        },
        ensure_ascii=False,
    )
    assert reco.extraire_corrections(sortie, "forme") == []


def test_marquage_style_original_egale_correction_conserve():
    """Style/Technique marquent SANS réécrire : original == correction est leur
    mode de marquage légitime — le rejet no-op ne concerne que la phase Forme."""
    sortie = json.dumps(
        {
            "corrections": [
                {
                    "id": "c-0001", "phase": "style", "type": "repetition",
                    "paragraphe_id": "p-1", "debut": 0, "fin": 3,
                    "original": "Les", "correction": "Les",
                    "explication": "Répétition.",
                }
            ]
        },
        ensure_ascii=False,
    )
    validees = reco.extraire_corrections(sortie, "style")
    assert [c.id for c in validees] == ["c-0001"]


# --- Invariants métier du contrat Correction (FA5) ----------------------------


def test_invariant_fin_superieure_a_debut():
    """FA5 : `fin <= debut` est structurellement invalide (fin exclusif, debut
    inclusif) — rejet Pydantic -> rejet individuel, sans arrêt du pipeline."""
    with pytest.raises(ValueError):
        _correction(debut=14, fin=14)
    with pytest.raises(ValueError):
        _correction(debut=18, fin=14)


def test_invariant_champs_non_vides():
    """FA5 : une correction sans type, sans fragment original ou sans
    explication pédagogique n'a aucun sens pour l'auteur — rejet."""
    for champ in ("type", "original", "explication"):
        with pytest.raises(ValueError):
            _correction(**{champ: ""})


def test_correction_suppression_correction_vide_autorisee():
    """La SUPPRESSION est légitime (ex. espace double, caractère superflu) :
    `correction` peut être vide — seul `original` doit être non vide."""
    correction = _correction(correction="")
    assert correction.correction == ""


def test_entree_bornes_incoherentes_rejetee_sans_arret():
    """Pipeline : une entrée LLM avec fin <= debut est rejetée individuellement
    (validation Pydantic), le reste de la liste est conservé."""
    sortie = json.dumps(
        {
            "corrections": [
                {
                    "id": "c-0001", "phase": "forme", "type": "accord",
                    "paragraphe_id": "p-1", "debut": 18, "fin": 14,
                    "original": "part", "correction": "partent",
                    "explication": "Accord.",
                },
                {
                    "id": "c-0002", "phase": "forme", "type": "accord",
                    "paragraphe_id": "p-1", "debut": 14, "fin": 18,
                    "original": "part", "correction": "partent",
                    "explication": "Accord.",
                },
            ]
        },
        ensure_ascii=False,
    )
    validees = reco.extraire_corrections(sortie, "forme")
    assert [c.id for c in validees] == ["c-0002"]


def test_schema_strict_reponse_corrections_genere_un_json_schema_complet():
    """FA5 : `ReponseCorrections` sert de schéma strict pour les Structured
    Outputs Mistral — toutes les propriétés du contrat y figurent."""
    from app.models import ReponseCorrections

    schema = ReponseCorrections.model_json_schema()
    assert schema["properties"]["corrections"]["type"] == "array"
    # Le contrat Correction est référencé via $defs/$ref (dédupliqué Pydantic)
    proprietes = schema["$defs"]["Correction"]["properties"]
    for champ in ("id", "phase", "type", "paragraphe_id", "debut", "fin",
                  "original", "correction", "explication"):
        assert champ in proprietes
    # Invariants FA5 reflétés dans le schéma transmis au LLM
    assert proprietes["original"].get("minLength") == 1
    assert proprietes["explication"].get("minLength") == 1
