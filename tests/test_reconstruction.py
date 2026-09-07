"""Tests du service de reconstruction (J2.5) : état initial, Forme par défaut,
refus/restauration, localisation ancrée, splices avec remappage déterministe,
préservation du formatage, réévaluation d'un paragraphe."""

from app.models import Correction, CorrectionFusionnee
from app.services import reconciliation, reconstruction
from app.services.texte_riche import ParagrapheRiche, RunFormat

TEXTE = "Les cavaliers part à l'aube vers la cité."


def _p(texte=TEXTE, pid="p-1", runs=None):
    if runs is None:
        runs = [RunFormat(texte=texte)]
    return ParagrapheRiche(id=pid, runs=runs)


def _fusion(cid, phase, debut, fin, original, correction, pid="p-1"):
    c = Correction(
        id=cid, phase=phase, type="test", paragraphe_id=pid,
        debut=debut, fin=fin, contexte_avant="Les cavaliers ", original=original,
        correction=correction, explication="Explication.", regle="",
        variantes=[],
    )
    return CorrectionFusionnee(correction=c)


def _courant(etat, pid="p-1"):
    return reconstruction.texte_paragraphe(etat, pid)


def test_etat_initial_applique_forme_par_defaut():
    etat = reconstruction.etat_initial(
        [_fusion("c-1", "forme", 14, 18, "part", "partent")], [_p()]
    )
    assert _courant(etat) == "Les cavaliers partent à l'aube vers la cité."
    assert etat["choix"] == {}


def test_etat_initial_preserve_le_formatage_du_run():
    runs = [
        RunFormat(texte="Les cavaliers "),
        RunFormat(texte="part", italique=True),
        RunFormat(texte=" à l'aube."),
    ]
    etat = reconstruction.etat_initial(
        [_fusion("c-1", "forme", 14, 18, "part", "partent")], [_p(runs=runs)]
    )
    p = etat["paragraphes"][0]
    insere = next(r for r in p.runs if r.texte == "partent")
    assert insere.italique is True
    assert _courant(etat) == "Les cavaliers partent à l'aube."


def test_etat_initial_style_sur_le_meme_fragment_est_remappe():
    etat = reconstruction.etat_initial(
        [
            _fusion("c-1", "forme", 14, 18, "part", "partent"),
            _fusion("c-2", "style", 14, 18, "part", "s'élancent"),
        ],
        [_p()],
    )
    style = next(e for e in etat["corrections"] if e["fusion"].correction.phase == "style")
    c = style["fusion"].correction
    assert c.debut == 14 and c.fin == 21  # couvre « partent » (7 car.) dans le texte courant
    assert _courant(etat)[c.debut:c.fin] == "partent"


def test_formes_en_chevauchement_la_premiere_garde_la_main():
    etat = reconstruction.etat_initial(
        [
            _fusion("c-1", "forme", 14, 18, "part", "partent"),
            _fusion("c-2", "forme", 16, 22, "art à", "avance à"),
        ],
        [_p()],
    )
    c2 = next(e for e in etat["corrections"] if e["fusion"].correction.id == "c-2")
    assert c2["etat"] == "obsolete"
    assert _courant(etat) == "Les cavaliers partent à l'aube vers la cité."


def test_refus_restitue_original_puis_reacceptation():
    etat = reconstruction.etat_initial(
        [_fusion("c-1", "forme", 14, 18, "part", "partent")], [_p()]
    )
    assert reconstruction.basculer_choix(etat, "c-1", "original") is True
    assert _courant(etat) == TEXTE
    assert etat["choix"]["c-1"] == "original"
    assert reconstruction.basculer_choix(etat, "c-1", "corrige") is True
    assert _courant(etat) == "Les cavaliers partent à l'aube vers la cité."
    assert "c-1" not in etat["choix"]


def test_refus_categorie_non_forme_refuse():
    etat = reconstruction.etat_initial(
        [_fusion("c-2", "style", 14, 18, "part", "s'élancent")], [_p()]
    )
    assert reconstruction.basculer_choix(etat, "c-2", "original") is False


def test_localiser_avec_ancre_occurrence_unique_et_echec():
    texte = "Le chat dort. Le chat rêve."
    assert reconstruction.localiser(texte, "chat", "Le ") == (3, 7)
    assert reconstruction.localiser(texte, "chat", "dort. Le ") == (17, 21)
    assert reconstruction.localiser(texte, "chat") is None  # ambigu sans ancre
    assert reconstruction.localiser(texte, "chien") is None


def test_modification_decale_les_corrections_suivantes():
    etat = reconstruction.etat_initial(
        [
            _fusion("c-1", "forme", 14, 18, "part", "partent"),
            _fusion("c-2", "style", 36, 40, "cité", "cité"),
        ],
        [_p()],
    )
    # Remplace un mot AVANT la correction Style → elle est décalée
    reconstruction.appliquer_modification(etat, "p-1", 0, 3, "Nos")  # Les → Nos
    style = next(e for e in etat["corrections"] if e["fusion"].correction.id == "c-2")
    c = style["fusion"].correction
    assert (c.debut, c.fin) == (39, 43)  # 36..40 → décalée de +3 par la Forme appliquée
    assert _courant(etat) == "Nos cavaliers partent à l'aube vers la cité."


def test_modification_manuelle_rend_la_forme_intersectee_obsolete():
    etat = reconstruction.etat_initial(
        [_fusion("c-1", "forme", 14, 18, "part", "partent")], [_p()]
    )
    # La Forme appliquée occupe désormais [14, 21) dans le texte courant (« partent »)
    reconstruction.appliquer_modification(etat, "p-1", 14, 21, "s'élancent")
    forme = next(e for e in etat["corrections"] if e["fusion"].correction.id == "c-1")
    assert forme["etat"] == "obsolete"
    assert "réévaluez" in forme["motif"]
    assert _courant(etat) == "Les cavaliers s'élancent à l'aube vers la cité."
    assert etat["modifies"] == ["p-1"]


def test_reevaluation_remplace_les_corrections_du_paragraphe():
    etat = reconstruction.etat_initial(
        [_fusion("c-1", "forme", 14, 18, "part", "partent")], [_p()]
    )
    nouvelle = _fusion("c-r1", "style", 14, 21, "partent", "partent")
    reconstruction.remplacer_corrections_paragraphe(etat, "p-1", [nouvelle])
    ids = [e["fusion"].correction.id for e in etat["corrections"]]
    assert ids == ["c-r1"]
    style = etat["corrections"][0]
    c = style["fusion"].correction
    assert _courant(etat)[c.debut:c.fin] == "partent"


def test_aller_retour_json_est_fidele():
    etat = reconstruction.etat_initial(
        [
            _fusion("c-1", "forme", 14, 18, "part", "partent"),
            _fusion("c-2", "style", 36, 40, "cité", "cité"),
        ],
        [_p()],
    )
    reconstruit = reconstruction.depuis_json(reconstruction.vers_json(etat))
    assert _courant(reconstruit) == _courant(etat)
    assert [e["fusion"].correction.id for e in reconstruit["corrections"]] == ["c-1", "c-2"]


def test_second_paragraphe_independant():
    p1 = _p(TEXTE, "p-1")
    p2 = _p("Le soir tombe sur la mer.", "p-2")
    etat = reconstruction.etat_initial(
        [
            _fusion("c-1", "forme", 14, 18, "part", "partent", pid="p-1"),
            _fusion("c-2", "style", 4, 8, "tombe", "tombe", pid="p-2"),
        ],
        [p1, p2],
    )
    assert _courant(etat, "p-1") == "Les cavaliers partent à l'aube vers la cité."
    assert _courant(etat, "p-2") == "Le soir tombe sur la mer."
    c2 = next(e for e in etat["corrections"] if e["fusion"].correction.id == "c-2")
    assert c2["fusion"].correction.debut == 4  # non décalée par la splice de p-1


# --- Jalon A : choix Forme indépendants après ids uniques ---------------------


def test_choix_forme_independants_apres_renumerotation():
    """Deux corrections émises avec le même id : après réassignation globale
    (jalon A), le choix Forme (clé = id) ne porte que sur SA correction."""
    fusions = reconciliation.renumeroter([
        _fusion("c-0001", "forme", 14, 18, "part", "partent"),
        _fusion("c-0001", "forme", 36, 40, "cité", "cités"),
    ])
    etat = reconstruction.etat_initial(fusions, [_p()])
    ids = [e["fusion"].correction.id for e in etat["corrections"]]
    assert len(set(ids)) == 2
    assert reconstruction.basculer_choix(etat, ids[0], "original") is True
    assert etat["choix"] == {ids[0]: "original"}  # l'autre Forme reste appliquée