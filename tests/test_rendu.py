"""Tests du rendu annoté en couches (J2.5) : segments, chevauchements superposés,
Forme refusée, corrections obsolètes, groupes g-XXXX, compteur de masqués."""

from app.models import Correction, CorrectionFusionnee
from app.services import reconstruction, rendu
from app.services.texte_riche import ParagrapheRiche, RunFormat

TEXTE = "Les sentinelles veille sur les remparts silencieux."


def _p(texte=TEXTE, pid="p-1", italique_de=None):
    """Un paragraphe riche ; `italique_de` : début d'une zone italique de 6 caractères."""
    if italique_de is None:
        runs = [RunFormat(texte=texte)]
    else:
        runs = [
            RunFormat(texte=texte[:italique_de]),
            RunFormat(texte=texte[italique_de:italique_de + 6], italique=True),
            RunFormat(texte=texte[italique_de + 6:]),
        ]
    return ParagrapheRiche(id=pid, runs=runs)


def _fusion(cid, phase, debut, fin, original, correction):
    c = Correction(
        id=cid, phase=phase, type="test", paragraphe_id="p-1",
        debut=debut, fin=fin, contexte_avant="", original=original,
        correction=correction, explication="Explication de test.", regle="Règle test",
        variantes=[],
    )
    return CorrectionFusionnee(correction=c)


def _doc(fusions, paragraphe=None):
    etat = reconstruction.etat_initial(fusions, [paragraphe or _p()])
    return rendu.preparer_document(
        etat["paragraphes"], etat["corrections"], etat["choix"], etat["modifies"]
    )


def test_correction_forme_segments_barré_et_inséré():
    doc = _doc([_fusion("c-1", "forme", 16, 22, "veille", "veillent")])
    assert doc["nb_masques"] == 0
    segments = doc["paragraphes"][0]["segments"]
    assert [s["type"] for s in segments] == ["texte", "forme", "texte"]
    assert segments[0]["texte"] == "Les sentinelles "
    assert segments[1]["del"] == "veille"
    assert segments[1]["ins"] == "veillent"
    assert segments[1]["groupe"].startswith("g-")


def test_forme_et_style_sur_le_meme_fragment_sempilent():
    doc = _doc([
        _fusion("c-1", "forme", 16, 22, "veille", "veillent"),
        _fusion("c-2", "style", 16, 22, "veille", "veillaient"),
    ])
    segments = doc["paragraphes"][0]["segments"]
    forme = segments[1]
    assert forme["type"] == "forme"
    assert "mark-style" in forme["classes"]  # le Style suit sur le texte corrigé
    # le style est remappé sur le fragment corrigé dans le texte courant
    style_info = next(i for i in doc["corrections_barre"] if i["phase"] == "style")
    courant = "".join(
        s.get("ins") or s.get("texte", "") for s in segments
    )
    assert courant[style_info["debut"]:style_info["fin"]] == "veillent"


def test_technique_fond_jaune_sur_texte_simple():
    doc = _doc([_fusion("c-3", "technique", 40, 50, "silencieux", "silencieux")])
    segments = doc["paragraphes"][0]["segments"]
    # aucun paragraphe vide : la technique marque le texte courant en jaune
    assert segments[0]["type"] == "texte"
    assert "mark-technique" in segments[0]["classes"]
    assert segments[0]["groupe"] is not None  # cliquable → détail dans la barre latérale


def test_forme_refusee_rend_le_texte_neutral_marque():
    etat = reconstruction.etat_initial(
        [_fusion("c-1", "forme", 16, 22, "veille", "veillent")], [_p()]
    )
    reconstruction.basculer_choix(etat, "c-1", "original")
    doc = rendu.preparer_document(
        etat["paragraphes"], etat["corrections"], etat["choix"], etat["modifies"]
    )
    segments = doc["paragraphes"][0]["segments"]
    assert [s["type"] for s in segments] == ["texte"]
    assert segments[0]["texte"] == TEXTE  # original restauré
    assert "refusee" in segments[0]["classes"]
    info = doc["corrections_barre"][0]
    assert info["decision"] == "original"


def test_correction_obsolete_ne_s_affiche_pas_dans_le_texte():
    etat = reconstruction.etat_initial(
        [_fusion("c-1", "forme", 16, 22, "veille", "veillent")], [_p()]
    )
    reconstruction.appliquer_modification(etat, "p-1", 16, 22, "monte la garde")
    doc = rendu.preparer_document(
        etat["paragraphes"], etat["corrections"], etat["choix"], etat["modifies"]
    )
    segments = doc["paragraphes"][0]["segments"]
    courant = "".join(s.get("ins") or s.get("texte", "") for s in segments)
    assert "monte la garde" in courant
    assert all(e["etat"] == "obsolete" for e in etat["corrections"])
    assert doc["paragraphes"][0]["edite"] is True


def test_formatage_preserve_sur_les_segments():
    p = _p(italique_de=16)  # « veille » en italique
    doc = _doc([_fusion("c-1", "forme", 16, 22, "veille", "veillent")], p)
    segments = doc["paragraphes"][0]["segments"]
    assert segments[1]["italique"] is True  # la correction hérite du formatage


def test_compteur_de_paragraphes_masques():
    p2 = ParagrapheRiche(id="p-2", runs=[RunFormat(texte="Rien à corriger ici.")])
    p3 = ParagrapheRiche(id="p-3", runs=[RunFormat(texte="Rien non plus.")])
    # paragraphe sans correction → masqué
    etat = reconstruction.etat_initial([], [p2, p3])
    doc_vide = rendu.preparer_document(etat["paragraphes"], etat["corrections"], etat["choix"])
    assert doc_vide["nb_masques"] == 2
    assert doc_vide["paragraphes"] == []