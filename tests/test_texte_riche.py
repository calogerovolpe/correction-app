"""Tests unitaires pour le module texte_riche (J2.2)."""

import json
from app.models import RunFormat, ParagrapheRiche
from app.services import texte_riche


def test_parser_texte_brut_legacy_en_paragraphes_riches():
    brut = "Premier paragraphe.\n\nDeuxième avec dialogue :\n— Bonjour !"
    riches = texte_riche.parser_document_riche(brut)
    assert len(riches) == 3
    assert riches[0].id == "p-1"
    assert riches[0].runs[0].texte == "Premier paragraphe."
    assert riches[2].runs[0].texte == "— Bonjour !"


def test_serialiser_et_parser_format_v2_json():
    p1 = ParagrapheRiche(
        id="p-1",
        runs=[
            RunFormat(texte="Le mot ", gras=False, italique=False, souligne=False),
            RunFormat(texte="important", gras=True, italique=True, souligne=False),
            RunFormat(texte=" est là.", gras=False, italique=False, souligne=False),
        ]
    )
    chaine_json = texte_riche.serialiser_document_riche([p1])
    repars = texte_riche.parser_document_riche(chaine_json)
    assert len(repars) == 1
    assert len(repars[0].runs) == 3
    assert repars[0].runs[1].gras is True
    assert repars[0].runs[1].italique is True


def test_decoupage_runs_par_intervalle_preservation_style():
    # "Bonjour le monde merveilleux"
    runs = [
        RunFormat(texte="Bonjour ", gras=True),
        RunFormat(texte="le monde ", italique=True),
        RunFormat(texte="merveilleux", souligne=True),
    ]
    # Intervalle ciblé : "le monde" dans "Bonjour le monde merveilleux" -> indices [8, 16)
    avant, milieu, apres = texte_riche.decouper_runs_par_intervalle(runs, 8, 17)
    assert len(avant) == 1
    assert avant[0].texte == "Bonjour "
    assert avant[0].gras is True

    assert len(milieu) == 1
    assert milieu[0].texte == "le monde "
    assert milieu[0].italique is True

    assert len(apres) == 1
    assert apres[0].texte == "merveilleux"
    assert apres[0].souligne is True


def test_extraire_mots_frequents_antirepetition():
    texte = (
        "Le capitaine regardait la mer. Le capitaine attendait le navire. "
        "Le capitaine pensait à la bataille et le capitaine espérait."
    )
    frequents = texte_riche.extraire_mots_frequents(texte)
    assert "capitaine" in frequents
