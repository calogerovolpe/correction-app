"""Tests du rendu annoté — v6 §7, §13 : segments, blocs multi, suggestions, groupes g-XXXX, compteur masques."""

from app.models import Correction, CorrectionFusionnee, EmbellissementMigre
from app.services import rendu
from app.services.normalisation import Paragraphe

P1 = Paragraphe(id="p-1", texte="Les sentinelles veille sur les remparts silencieux.")


def _fusion(cid, phase, debut, fin, original, correction, variantes=None, migre=None):
    c = Correction(
        id=cid, phase=phase, type="accord_sujet_verbe", paragraphe_id="p-1",
        debut=debut, fin=fin, contexte_avant="", original=original,
        correction=correction, explication="Explication de test.", regle="Règle test",
        variantes=variantes or [],
    )
    return CorrectionFusionnee(correction=c, embellissement_migre=migre)


def test_correction_simple_segments():
    doc = rendu.preparer_document(
        [_fusion("c-1", "forme", 16, 22, "veille", "veillent")], [P1]
    )
    assert doc["nb_masques"] == 0
    segments = doc["paragraphes"][0]["segments"]
    assert [s["type"] for s in segments] == ["texte", "simple", "texte"]
    assert segments[0]["texte"] == "Les sentinelles "
    assert segments[1]["original"] == "veille"
    assert segments[1]["texte"] == "veillent"
    assert segments[1]["groupe"].startswith("g-")  # calculé par Python (v6 §0-8)


def test_bloc_multi_ordre_fixe():
    # Deux corrections sur le même fragment : bloc multi, ordre Forme -> Technique (v6 §7.3.2)
    doc = rendu.preparer_document(
        [
            _fusion("c-2", "technique", 16, 22, "veille", "veillaient"),
            _fusion("c-1", "forme", 16, 22, "veille", "veillent"),
        ],
        [P1],
    )
    segments = doc["paragraphes"][0]["segments"]
    assert [s["type"] for s in segments] == ["texte", "multi", "texte"]
    assert [i["phase"] for i in segments[1]["ins"]] == ["forme", "technique"]
    assert segments[1]["original"] == "veille"
    assert [cas["phase"] for cas in segments[1]["cas"]] == ["forme", "technique"]


def test_embellissement_isole_suggestion_jamais_barre():
    doc = rendu.preparer_document(
        [_fusion("c-3", "embellissement", 40, 50, "silencieux", "silencieux et sombre",
                 variantes=["muets"])],
        [P1],
    )
    seg = doc["paragraphes"][0]["segments"][1]
    assert seg["type"] == "suggestion"  # <mark class="sugg">, jamais barré (v6 §7.3.3)
    assert seg["suggestion"] == "silencieux et sombre"
    assert seg["variantes"] == ["muets"]


def test_style_hote_embellissement_migre():
    migre = EmbellissementMigre(
        suggestion="veillent sans relâche", variantes=["veillaient"], explication="Prosodie."
    )
    doc = rendu.preparer_document(
        [_fusion("c-4", "style", 16, 22, "veille", "veillent", migre=migre)], [P1]
    )
    seg = doc["paragraphes"][0]["segments"][1]
    assert seg["type"] == "simple"  # correction Style normale (v6 §8.4 : Style prioritaire)
    cas = seg["cas"][0]
    assert cas["embellissement"]["suggestion"] == "veillent sans relâche"


def test_compteur_de_paragraphes_masques():
    # Seuls les paragraphes corrigés sont affichés (v6 §7.1)
    p2 = Paragraphe(id="p-2", texte="Rien à corriger ici.")
    p3 = Paragraphe(id="p-3", texte="Rien non plus.")
    doc = rendu.preparer_document([_fusion("c-5", "forme", 16, 22, "veille", "veillent")],
                                  [P1, p2, p3])
    assert doc["nb_masques"] == 2
    assert len(doc["paragraphes"]) == 1
    assert doc["paragraphes"][0]["id"] == "p-1"


def test_document_vide_liste_valide():
    doc = rendu.preparer_document([], [P1])
    assert doc["paragraphes"] == []
    assert doc["nb_masques"] == 1
