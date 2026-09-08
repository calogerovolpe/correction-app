"""Tests du rendu annoté en couches (J2.5) : segments, chevauchements superposés,
Forme refusée, corrections obsolètes, groupes g-XXXX, compteur de masqués."""

from app.models import Correction, CorrectionFusionnee
from app.services import reconstruction, rendu
from app.services.reconciliation import renumeroter
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


# --- Jalon A : ids de correction uniques entre phases -------------------------


def test_ids_dupliques_entre_phases_groupes_et_barre_distincts():
    """Deux phases émettent le même id « c-0001 » : après réassignation globale
    (analyse.py appelle renumeroter), le rendu produit 2 groupes distincts et
    2 entrées de barre latérale distinctes — avant le correctif, le dict
    `groupes` (clé = id) collait les deux corrections sur un même data-groupe."""
    forme = _fusion("c-0001", "forme", 16, 22, "veille", "veillent")
    style = _fusion("c-0001", "style", 16, 22, "veille", "veillaient")
    fusion = renumeroter([forme, style])
    assert len({f.correction.id for f in fusion}) == 2  # ids réassignés uniques
    doc = _doc(fusion)
    infos = doc["corrections_barre"]
    assert len(infos) == 2
    g_forme = next(i["groupe"] for i in infos if i["phase"] == "forme")
    g_style = next(i["groupe"] for i in infos if i["phase"] == "style")
    assert g_forme != g_style
    seg_forme = next(s for s in doc["paragraphes"][0]["segments"] if s["type"] == "forme")
    assert seg_forme["groupe"] == g_forme  # le clic cible la BONNE correction


# --- Jalon R1-a : projection par phase (onglets) --------------------------------


def _etat_deux_phases():
    etat = reconstruction.etat_initial(
        [
            _fusion("c-1", "forme", 16, 22, "veille", "veillent"),
            _fusion("c-2", "style", 40, 50, "silencieux", "silencieux"),
        ],
        [_p()],
    )
    return etat


def test_projection_par_phase_n_affiche_que_sa_phase():
    """Chaque onglet ne montre QUE les corrections de sa phase : la projection
    filtre les `entrees` puis réutilise `preparer_document` (logique unique)."""
    etat = _etat_deux_phases()

    doc_forme = rendu.preparer_document_par_phase(
        etat["paragraphes"], etat["corrections"], "forme",
        etat["choix"], etat["modifies"],
    )
    segments = doc_forme["paragraphes"][0]["segments"]
    assert [s["type"] for s in segments] == ["texte", "forme", "texte"]
    assert all("mark-style" not in s["classes"] for s in segments)
    assert [i["phase"] for i in doc_forme["corrections_barre"]] == ["forme"]

    doc_style = rendu.preparer_document_par_phase(
        etat["paragraphes"], etat["corrections"], "style",
        etat["choix"], etat["modifies"],
    )
    segments = doc_style["paragraphes"][0]["segments"]
    assert all(s["type"] == "texte" for s in segments)  # aucune Forme appliquée ici
    assert any("mark-style" in s["classes"] for s in segments)
    assert [i["phase"] for i in doc_style["corrections_barre"]] == ["style"]


def test_tout_reste_la_superposition_complete():
    """Régression : `preparer_document` (onglet « Tout ») reste inchangée —
    les deux phases restent superposées dans la même vue."""
    etat = _etat_deux_phases()
    doc = rendu.preparer_document(
        etat["paragraphes"], etat["corrections"], etat["choix"], etat["modifies"]
    )
    assert [i["phase"] for i in doc["corrections_barre"]] == ["forme", "style"]
    segments = doc["paragraphes"][0]["segments"]
    assert any(s["type"] == "forme" for s in segments)
    assert any("mark-style" in s["classes"] for s in segments if s["type"] == "texte")


def test_projection_phase_absente_rend_le_texte_neutre():
    """Aucune correction de la phase : aucun paragraphe actif → le texte est
    masqué (comportement existant de `preparer_document` conservé)."""
    etat = _etat_deux_phases()
    doc = rendu.preparer_document_par_phase(
        etat["paragraphes"], etat["corrections"], "technique",
        etat["choix"], etat["modifies"],
    )
    assert doc["corrections_barre"] == []
    assert doc["paragraphes"] == []
    assert doc["nb_masques"] == 1