"""Tests du service de reconstruction (J2.5 → R2) : base immuable + annotations,
projection du texte courant, refus Forme = filtre (aucun remappage), patches
manuels ancrés base, offsets de correction JAMAIS décalés, réancrage de la
réévaluation, migration de l'ancien format."""

from app.models import Correction
from app.services import reconciliation, reconstruction
from app.services.texte_riche import ParagrapheRiche, RunFormat

TEXTE = "Les cavaliers part à l'aube vers la cité."


def _p(texte=TEXTE, pid="p-1", runs=None):
    if runs is None:
        runs = [RunFormat(texte=texte)]
    return ParagrapheRiche(id=pid, runs=runs)


def _corr(cid, phase, debut, fin, original, correction, pid="p-1"):
    return Correction(
        id=cid, phase=phase, type="test", paragraphe_id=pid,
        debut=debut, fin=fin, contexte_avant="Les cavaliers ", original=original,
        correction=correction, explication="Explication.", regle="",
        variantes=[],
    )


def _courant(etat, pid="p-1"):
    return reconstruction.texte_paragraphe(etat, pid)


def _projeter_correction(etat, cid, pid="p-1"):
    """Retourne (debut, fin) PROJETÉS d'une correction dans le texte courant."""
    _, entrees = reconstruction.projeter_paragraphe(etat, pid)
    entree = next(e for e in entrees if e["correction"].id == cid)
    c = entree["correction"]
    return c.debut, c.fin


def test_etat_initial_applique_forme_par_defaut():
    etat = reconstruction.etat_initial(
        [_corr("c-1", "forme", 14, 18, "part", "partent")], [_p()]
    )
    assert _courant(etat) == "Les cavaliers partent à l'aube vers la cité."
    assert etat["choix"] == {}
    # R2 : la base est IMMUABLE — la Forme n'est jamais écrite dans le texte source
    assert etat["base"][0].runs[0].texte == TEXTE


def test_etat_initial_preserve_le_formatage_du_run():
    runs = [
        RunFormat(texte="Les cavaliers "),
        RunFormat(texte="part", italique=True),
        RunFormat(texte=" à l'aube."),
    ]
    etat = reconstruction.etat_initial(
        [_corr("c-1", "forme", 14, 18, "part", "partent")], [_p(runs=runs)]
    )
    projetes, _ = reconstruction.projeter_paragraphes(etat)
    insere = next(r for r in projetes[0].runs if r.texte == "partent")
    assert insere.italique is True
    assert _courant(etat) == "Les cavaliers partent à l'aube."
    assert etat["base"][0].runs == runs  # la base conserve le formatage d'origine


def test_etat_initial_style_non_decale_mais_projete_sur_le_corrige():
    etat = reconstruction.etat_initial(
        [
            _corr("c-1", "forme", 14, 18, "part", "partent"),
            _corr("c-2", "style", 14, 18, "part", "s'élancent"),
        ],
        [_p()],
    )
    # R2 : la Style GARDE ses offsets d'origine (base) — elle n'est plus remappée
    style = next(e for e in etat["corrections"] if e["correction"].phase == "style")
    c = style["correction"]
    assert (c.debut, c.fin) == (14, 18)
    # …mais sa projection couvre « partent » (7 car.) dans le texte courant
    assert _projeter_correction(etat, "c-2") == (14, 21)
    assert _courant(etat)[14:21] == "partent"


def test_formes_en_chevauchement_la_premiere_garde_la_main():
    etat = reconstruction.etat_initial(
        [
            _corr("c-1", "forme", 14, 18, "part", "partent"),
            _corr("c-2", "forme", 16, 22, "art à", "avance à"),
        ],
        [_p()],
    )
    c2 = next(e for e in etat["corrections"] if e["correction"].id == "c-2")
    assert c2["etat"] == "obsolete"
    assert _courant(etat) == "Les cavaliers partent à l'aube vers la cité."


def test_refus_restitue_original_puis_reacceptation():
    etat = reconstruction.etat_initial(
        [_corr("c-1", "forme", 14, 18, "part", "partent")], [_p()]
    )
    assert reconstruction.basculer_choix(etat, "c-1", "original") is True
    assert _courant(etat) == TEXTE
    assert etat["choix"]["c-1"] == "original"
    assert reconstruction.basculer_choix(etat, "c-1", "corrige") is True
    assert _courant(etat) == "Les cavaliers partent à l'aube vers la cité."
    assert "c-1" not in etat["choix"]


def test_refus_categorie_non_forme_refuse():
    etat = reconstruction.etat_initial(
        [_corr("c-2", "style", 14, 18, "part", "s'élancent")], [_p()]
    )
    assert reconstruction.basculer_choix(etat, "c-2", "original") is False


def test_localiser_avec_ancre_occurrence_unique_et_echec():
    texte = "Le chat dort. Le chat rêve."
    assert reconstruction.localiser(texte, "chat", "Le ") == (3, 7)
    assert reconstruction.localiser(texte, "chat", "dort. Le ") == (17, 21)
    assert reconstruction.localiser(texte, "chat") is None  # ambigu sans ancre
    assert reconstruction.localiser(texte, "chien") is None


def test_modification_ne_decale_jamais_les_corrections():
    etat = reconstruction.etat_initial(
        [
            _corr("c-1", "forme", 14, 18, "part", "partent"),
            _corr("c-2", "style", 36, 40, "cité", "cité"),
        ],
        [_p()],
    )
    # Remplace un mot AVANT la correction Style : la Style ne bouge PLUS
    reconstruction.appliquer_modification(etat, "p-1", 0, 3, "Nos")  # Les → Nos
    style = next(e for e in etat["corrections"] if e["correction"].id == "c-2")
    c = style["correction"]
    assert (c.debut, c.fin) == (36, 40)  # coordonnées BASE conservées — jamais décalées
    # la projection, elle, la positionne sur « cité » (décalée de +3 au rendu)
    assert _projeter_correction(etat, "c-2") == (39, 43)
    assert _courant(etat) == "Nos cavaliers partent à l'aube vers la cité."


def test_modification_manuelle_rend_la_forme_intersectee_obsolete():
    etat = reconstruction.etat_initial(
        [_corr("c-1", "forme", 14, 18, "part", "partent")], [_p()]
    )
    # [14, 21) dans le texte courant = « partent », la Forme est intersectée
    reconstruction.appliquer_modification(etat, "p-1", 14, 21, "s'élancent")
    forme = next(e for e in etat["corrections"] if e["correction"].id == "c-1")
    assert forme["etat"] == "obsolete"
    assert "réévaluez" in forme["motif"]
    assert _courant(etat) == "Les cavaliers s'élancent à l'aube vers la cité."
    assert etat["modifies"] == ["p-1"]
    # le patch est ancré sur la zone de base que la Forme couvrait
    assert etat["patches"][0]["debut"] == 14 and etat["patches"][0]["fin"] == 18


def test_zone_deja_modifiee_refuse_le_recouvrement():
    etat = reconstruction.etat_initial(
        [_corr("c-1", "forme", 14, 18, "part", "partent")], [_p()]
    )
    reconstruction.appliquer_modification(etat, "p-1", 14, 21, "s'élancent")
    try:
        # couper le texte du patch (« s'é ») est impossible à ré-ancrer sur la base
        reconstruction.appliquer_modification(etat, "p-1", 14, 16, "x")
    except reconstruction.ZoneDejaModifiee:
        pass
    else:
        raise AssertionError(
            "Une sélection coupant une zone déjà modifiée devait être refusée"
        )
    assert len(etat["patches"]) == 1  # l'état n'a pas bougé


def test_reevaluation_reancre_les_corrections_sur_la_base():
    etat = reconstruction.etat_initial(
        [_corr("c-1", "forme", 14, 18, "part", "partent")], [_p()]
    )
    # la réévaluation retourne une correction en coordonnées du texte COURANT
    nouvelle = _corr("c-r1", "style", 14, 21, "partent", "partent")
    reconstruction.remplacer_corrections_paragraphe(etat, "p-1", [nouvelle])
    ids = [e["correction"].id for e in etat["corrections"]]
    assert ids == ["c-r1"]
    c = etat["corrections"][0]["correction"]
    # ré-ancrée sur la base : elle couvre « part » (4 car.) d'origine
    assert (c.debut, c.fin) == (14, 18)
    assert _courant(etat)[c.debut:c.fin] == "part"
    # et sa projection couvre « partent » dans le texte courant
    assert _projeter_correction(etat, "c-r1") == (14, 21)


def test_reevaluation_ancre_une_correction_sur_un_patch_manuel():
    """Après un embellissement (patch manuel), la réévaluation peut retourner
    une correction portant sur le TEXTE EMBELLI : elle est ancrée sur la zone du
    patch (base) et gagne dans la projection (rendu cohérent)."""
    etat = reconstruction.etat_initial(
        [_corr("c-1", "forme", 14, 18, "part", "partent")], [_p()]
    )
    reconstruction.appliquer_modification(etat, "p-1", 14, 21, "s'élancent")
    correction_embellie = _corr(
        "c-r1", "forme", 14, 24, "s'élancent", "s'élancèrent"
    )
    reconstruction.remplacer_corrections_paragraphe(etat, "p-1", [correction_embellie])
    c = etat["corrections"][0]["correction"]
    assert (c.debut, c.fin) == (14, 18)  # ancrée sur la zone du patch (base)
    assert _courant(etat) == "Les cavaliers s'élancèrent à l'aube vers la cité."


def test_aller_retour_json_est_fidele():
    etat = reconstruction.etat_initial(
        [
            _corr("c-1", "forme", 14, 18, "part", "partent"),
            _corr("c-2", "style", 36, 40, "cité", "cité"),
        ],
        [_p()],
    )
    reconstruit = reconstruction.depuis_json(reconstruction.vers_json(etat))
    assert _courant(reconstruit) == _courant(etat)
    assert [e["correction"].id for e in reconstruit["corrections"]] == ["c-1", "c-2"]


def test_aller_retour_json_conserve_choix_et_patches():
    etat = reconstruction.etat_initial(
        [_corr("c-1", "forme", 14, 18, "part", "partent")], [_p()]
    )
    reconstruction.basculer_choix(etat, "c-1", "original")
    reconstruction.appliquer_modification(etat, "p-1", 0, 3, "Nos")
    reconstruit = reconstruction.depuis_json(reconstruction.vers_json(etat))
    assert reconstruit["choix"] == {"c-1": "original"}
    assert len(reconstruit["patches"]) == 1
    assert _courant(reconstruit) == _courant(etat)


def test_second_paragraphe_independant():
    p1 = _p(TEXTE, "p-1")
    p2 = _p("Le soir tombe sur la mer.", "p-2")
    etat = reconstruction.etat_initial(
        [
            _corr("c-1", "forme", 14, 18, "part", "partent", pid="p-1"),
            _corr("c-2", "style", 4, 8, "tombe", "tombe", pid="p-2"),
        ],
        [p1, p2],
    )
    assert _courant(etat, "p-1") == "Les cavaliers partent à l'aube vers la cité."
    assert _courant(etat, "p-2") == "Le soir tombe sur la mer."
    c2 = next(e for e in etat["corrections"] if e["correction"].id == "c-2")
    assert c2["correction"].debut == 4  # jamais décalée par un autre paragraphe


# --- Jalon A : choix Forme indépendants après ids uniques ---------------------


def test_choix_forme_independants_apres_renumerotation():
    """Deux corrections émises avec le même id : après réassignation globale
    (jalon A), le choix Forme (clé = id) ne porte que sur SA correction."""
    corrections = reconciliation.renumeroter([
        _corr("c-0001", "forme", 14, 18, "part", "partent"),
        _corr("c-0001", "forme", 36, 40, "cité", "cités"),
    ])
    etat = reconstruction.etat_initial(corrections, [_p()])
    ids = [e["correction"].id for e in etat["corrections"]]
    assert len(set(ids)) == 2
    assert reconstruction.basculer_choix(etat, ids[0], "original") is True
    assert etat["choix"] == {ids[0]: "original"}  # l'autre Forme reste appliquée


# --- Jalon R2 : migration de l'ancien format ---------------------------------


def test_est_ancien_format_detecte_les_deux_formats():
    assert reconstruction.est_ancien_format({"paragraphes": []}) is True
    assert reconstruction.est_ancien_format(
        {"modele": reconstruction.MODELE_ETAT, "base": []}
    ) is False


def test_migration_ancien_format_preserve_les_choix():
    """Migration R2 : base et corrections reconstruites depuis les sources ;
    les CHOIX/refus de l'auteur sont préservés par id, les modifications
    manuelles abandonnées (décision)."""
    corrections = [
        _corr("c-0001", "forme", 14, 18, "part", "partent"),
        _corr("c-0002", "style", 36, 40, "cité", "cité"),
    ]
    ancien = {
        "paragraphes": [{"id": "p-1", "runs": [{"texte": TEXTE}]}],
        "corrections": [
            {"correction": c.model_dump(), "etat": "active", "motif": None}
            for c in corrections
        ],
        "choix": {"c-0001": "original"},  # l'auteur avait refusé cette Forme
    }
    etat = reconstruction.migrer_ancien_format(ancien, [_p()], corrections)
    assert etat["choix"] == {"c-0001": "original"}
    assert etat["patches"] == []  # modifications manuelles abandonnées
    assert _courant(etat) == TEXTE  # le refus est effectif dans la projection
    # un choix dont l'id n'existe plus (renumérotation) est écarté
    ancien["choix"]["c-zzzz"] = "original"
    etat2 = reconstruction.migrer_ancien_format(ancien, [_p()], corrections)
    assert etat2["choix"] == {"c-0001": "original"}


def test_migration_ancien_format_conserve_les_etats_obsoletes():
    """Un état antérieur où une Forme était marquée obsolète (chevauchement ou
    modification manuelle) conserve ce marquage à la migration."""
    corrections = [
        _corr("c-0001", "forme", 14, 18, "part", "partent"),
        _corr("c-0002", "forme", 16, 22, "art à", "avance à"),
    ]
    ancien_base = {
        "id": "p-1",
        "runs": [{"texte": TEXTE}],
    }
    ancien = {
        "paragraphes": [ancien_base],
        "corrections": [
            {"correction": corrections[0].model_dump(), "etat": "active", "motif": None},
            {
                "correction": corrections[1].model_dump(),
                "etat": "obsolete",
                "motif": "Chevauche une autre correction Forme — non appliquée.",
            },
        ],
        "choix": {},
    }
    etat = reconstruction.migrer_ancien_format(
        ancien, [ParagrapheRiche.model_validate(ancien_base)], corrections
    )
    etats = {e["correction"].id: e["etat"] for e in etat["corrections"]}
    assert etats == {"c-0001": "active", "c-0002": "obsolete"}
    assert _courant(etat) == "Les cavaliers partent à l'aube vers la cité."