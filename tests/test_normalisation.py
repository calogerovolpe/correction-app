"""Tests de normalisation — v6 §8.1 et §5.2 (critères J1 : CRLF/BOM, paragraphes, titres, catégories)."""

import pytest

from app.services import normalisation as norm
from app.services.normalisation import TexteTropLong


def test_bom_crlf_et_fins_de_ligne():
    brut = "﻿Le chat.\r\n dort.  \r\n\r\nSuite."
    resultat = norm.normaliser(brut)
    assert "\ufeff" not in resultat
    assert "\r" not in resultat
    assert resultat == "Le chat.\n dort.\n\nSuite."


def test_decoupage_base_1_et_dialogues_memes_paragraphes():
    texte = "Premier paragraphe.\n\nDeuxième.\nRéplique B.\n\nTroisième."
    paragraphes = norm.decouper_paragraphes(texte)
    assert [p.id for p in paragraphes] == ["p-1", "p-2", "p-3"]
    # Saut de ligne simple = même paragraphe (v6 §8.1)
    assert paragraphes[1].texte == "Deuxième.\nRéplique B."


def test_decoupage_ignore_blocs_vides():
    paragraphes = norm.decouper_paragraphes("\n\n  \n\nUn seul.\n\n\n")
    assert [p.id for p in paragraphes] == ["p-1"]
    assert paragraphes[0].texte == "Un seul."


def test_titre_numerique_premiere_ligne_uniquement():
    numero, titre = norm.extraire_titre_chapitre("12 : La nuit tombe\n\nTexte.")
    assert numero == 12.0
    assert titre == "La nuit tombe"
    # La même structure numérique AILLEURS dans le texte n'est jamais un titre (v6 §5.2)
    assert norm.extraire_titre_chapitre("Il écrivit :\n\n1789 : la prise de la Bastille.") is None


def test_titre_decimal():
    numero, _ = norm.extraire_titre_chapitre("2.5 : Interlude")
    assert numero == 2.5


def test_prologue_reconnu_comme_titre_zero():
    assert norm.extraire_titre_chapitre("Prologue\n\nTexte.") == (0.0, "Prologue")
    # « Prologue : texte » n'est ni la regex numérique ni le mot exact
    assert norm.extraire_titre_chapitre("Prologue : texte\n\nSuite.") is None


def test_categories():
    # Titre valide = Chapitre quel que soit le nombre de paragraphes (seuil abaissé v6 §0-7)
    assert norm.detecter_categorie("1 : Titre\n\nUn seul paragraphe.") == "chapitre"
    assert norm.detecter_categorie("Un.\n\nDeux.\n\nTrois.") == "passage"
    assert norm.detecter_categorie("Un.\n\nDeux.") == "extrait"
    assert norm.detecter_categorie("Texte court sans structure.") == "extrait"


def test_garde_fou_taille():
    with pytest.raises(TexteTropLong):
        norm.verifier_taille("x" * 51, 50)
    norm.verifier_taille("x" * 50, 50)  # limite exacte : acceptée