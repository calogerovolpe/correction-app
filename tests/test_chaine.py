"""Tests de la machine d'états N+1 et du remplacement officiel — v6 §6.5, §6.6
(critère J1 : conforme / N=N sans remplacement -> Extrait / remplacement valide / refus)."""

from app.services import chaine


def _projet(courant=None, statut="vierge"):
    return {
        "projet_id": "P-TEST",
        "titre": "Roman test",
        "current_chapter_num": courant,
        "chain_status": statut,
    }


# --- Chaîne N+1 (v6 §6.5) ----------------------------------------------------


def test_vierge_prologue_et_chapitre_1_conformes():
    assert chaine.arbitrer(_projet(), 0.0).decision == "conforme"  # Prologue = 0
    assert chaine.arbitrer(_projet(), 1.0).decision == "conforme"


def test_vierge_autre_numero_reclasse():
    resultat = chaine.arbitrer(_projet(), 5.0)
    assert resultat.decision == "reclassement_extrait"
    assert resultat.categorie == "extrait"
    assert "codex" in resultat.message  # message de bannière (v6 §6.5 règle 4)


def test_conforme_n_plus_1():
    assert chaine.arbitrer(_projet(3, "ok"), 4.0).decision == "conforme"


def test_n_egal_n_sans_remplacement_reclasse_en_extrait():
    resultat = chaine.arbitrer(_projet(3, "ok"), 3.0)
    assert resultat.decision == "reclassement_extrait"  # v6 §6.5 règle 3
    assert resultat.categorie == "extrait"
    assert "Remplacer" in resultat.message


def test_n_egal_n_avec_remplacement_officiel():
    resultat = chaine.arbitrer(_projet(3, "ok"), 3.0, remplacement_demande=True)
    assert resultat.decision == "remplacement_officiel"  # v6 §6.5 règle 2
    assert resultat.categorie == "chapitre"


def test_chapitre_anterieur_reclasse():
    assert chaine.arbitrer(_projet(3, "ok"), 2.0).decision == "reclassement_extrait"


def test_trou_reclasse():
    assert chaine.arbitrer(_projet(3, "ok"), 6.0).decision == "reclassement_extrait"


def test_numero_decimal_reclasse():
    assert chaine.arbitrer(_projet(3, "ok"), 3.5).decision == "reclassement_extrait"


def test_recuperation_apres_rupture():
    # chain_status='rupture' : attendu = courant+1, jamais modifié par un reclassement
    assert chaine.arbitrer(_projet(3, "rupture"), 4.0).decision == "conforme"


def test_resoumission_du_prologue():
    # v6 §0-4 : Prologue reconnu dans tous les cas ; current=0 -> N=N
    assert (
        chaine.arbitrer(_projet(0, "ok"), 0.0, remplacement_demande=True).decision
        == "remplacement_officiel"
    )
    assert chaine.arbitrer(_projet(0, "ok"), 0.0).decision == "reclassement_extrait"


def test_forage_passe_la_chaine():
    resultat = chaine.arbitrer(_projet(3, "ok"), 99.0, categorie_forcee="passage")
    assert resultat.decision == "forcage" and resultat.categorie == "passage"
    resultat = chaine.arbitrer(_projet(3, "ok"), None, categorie_forcee="extrait")
    assert resultat.decision == "forcage" and resultat.categorie == "extrait"


def test_hors_chaine_rend_la_categorie_naturelle():
    resultat = chaine.arbitrer(_projet(3, "ok"), None, categorie_naturelle="passage")
    assert resultat.decision == "hors_chaine" and resultat.categorie == "passage"


# --- Remplacement officiel, préconditions /maj (v6 §6.6) --------------------


def test_remplacement_valide_numero_omis():
    resultat = chaine.valider_remplacement(_projet(3, "ok"), {3}, None)
    assert resultat.decision == "remplacement_officiel"


def test_remplacement_refuse_chapitre_jamais_soumis():
    resultat = chaine.valider_remplacement(_projet(3, "ok"), {1, 2, 3}, 4)
    assert resultat.decision == "refus_remplacement"
    assert "jamais été soumis" in resultat.message


def test_remplacement_refuse_numero_non_courant():
    resultat = chaine.valider_remplacement(_projet(3, "ok"), {1, 2, 3}, 2)
    assert resultat.decision == "refus_remplacement"
    assert "N=N" in resultat.message


def test_remplacement_refuse_session_vierge():
    resultat = chaine.valider_remplacement(_projet(None), set(), None)
    assert resultat.decision == "refus_remplacement"