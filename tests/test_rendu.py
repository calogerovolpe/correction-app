"""Tests du rendu annoté en couches (J2.5) : segments, chevauchements superposés,
Forme refusée, corrections obsolètes, groupes g-XXXX, compteur de masqués."""

from app.models import Correction
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


def _corr(cid, phase, debut, fin, original, correction):
    return Correction(
        id=cid, phase=phase, type="test", paragraphe_id="p-1",
        debut=debut, fin=fin, contexte_avant="", original=original,
        correction=correction, explication="Explication de test.", regle="Règle test",
        variantes=[],
    )


def _doc(fusions, paragraphe=None):
    etat = reconstruction.etat_initial(fusions, [paragraphe or _p()])
    return rendu.preparer_document_depuis_etat(etat)


def test_correction_forme_segments_barré_et_inséré():
    doc = _doc([_corr("c-1", "forme", 16, 22, "veille", "veillent")])
    assert doc["nb_masques"] == 0
    segments = doc["paragraphes"][0]["segments"]
    assert [s["type"] for s in segments] == ["texte", "forme", "texte"]
    assert segments[0]["texte"] == "Les sentinelles "
    assert segments[1]["del"] == "veille"
    assert segments[1]["ins"] == "veillent"
    assert segments[1]["groupe"].startswith("g-")


def test_forme_et_style_sur_le_meme_fragment_sempilent():
    doc = _doc([
        _corr("c-1", "forme", 16, 22, "veille", "veillent"),
        _corr("c-2", "style", 16, 22, "veille", "veillaient"),
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
    doc = _doc([_corr("c-3", "technique", 40, 50, "silencieux", "silencieux")])
    segments = doc["paragraphes"][0]["segments"]
    # FA3 — segmentation atomique : seule la zone [40, 50) porte le fond jaune
    marqués = [s for s in segments if s["type"] == "texte" and "mark-technique" in s["classes"]]
    assert marqués, "la zone Technique doit être marquée"
    courant = "".join(s["texte"] for s in segments)
    position = 0
    for s in segments:
        if "mark-technique" in s["classes"]:
            assert courant[position:position + len(s["texte"])] == "silencieux"
        position += len(s["texte"])
    assert marqués[0]["groupe"] is not None  # cliquable → détail dans la barre latérale


def test_forme_refusee_rend_le_texte_neutral_marque():
    etat = reconstruction.etat_initial(
        [_corr("c-1", "forme", 16, 22, "veille", "veillent")], [_p()]
    )
    reconstruction.basculer_choix(etat, "c-1", "original")
    doc = rendu.preparer_document_depuis_etat(etat)
    segments = doc["paragraphes"][0]["segments"]
    # FA3 — segmentation atomique : la zone refusée [16, 22) est découpée aux
    # bornes (segments texte de part et d'autre) et porte la classe `refusee`
    assert all(s["type"] == "texte" for s in segments)
    assert "".join(s["texte"] for s in segments) == TEXTE  # original restauré
    refusés = [s for s in segments if "refusee" in s["classes"]]
    assert refusés
    assert "".join(s["texte"] for s in refusés) == "veille"
    # les segments hors zone refusée sont neutres : avant [0,16) et après [22, fin)
    neutres = [s for s in segments if "refusee" not in s["classes"]]
    assert "".join(s["texte"] for s in neutres) == "Les sentinelles  sur les remparts silencieux."
    info = doc["corrections_barre"][0]
    assert info["decision"] == "original"


def test_correction_obsolete_ne_s_affiche_pas_dans_le_texte():
    etat = reconstruction.etat_initial(
        [_corr("c-1", "forme", 16, 22, "veille", "veillent")], [_p()]
    )
    reconstruction.appliquer_modification(etat, "p-1", 16, 22, "monte la garde")
    doc = rendu.preparer_document_depuis_etat(etat)
    segments = doc["paragraphes"][0]["segments"]
    courant = "".join(s.get("ins") or s.get("texte", "") for s in segments)
    assert "monte la garde" in courant
    assert all(e["etat"] == "obsolete" for e in etat["corrections"])
    assert doc["paragraphes"][0]["edite"] is True


def test_formatage_preserve_sur_les_segments():
    p = _p(italique_de=16)  # « veille » en italique
    doc = _doc([_corr("c-1", "forme", 16, 22, "veille", "veillent")], p)
    segments = doc["paragraphes"][0]["segments"]
    assert segments[1]["italique"] is True  # la correction hérite du formatage


def test_compteur_de_paragraphes_masques():
    p2 = ParagrapheRiche(id="p-2", runs=[RunFormat(texte="Rien à corriger ici.")])
    p3 = ParagrapheRiche(id="p-3", runs=[RunFormat(texte="Rien non plus.")])
    # paragraphe sans correction → éligible au masquage (compteur conservé)
    etat = reconstruction.etat_initial([], [p2, p3])
    doc_vide = rendu.preparer_document_depuis_etat(etat)
    assert doc_vide["nb_masques"] == 2
    # FA3 — document complet : les paragraphes sont TOUS exposés (le toggle
    # client filtre en mémoire) ; décision 35, fin du filtrage prématuré backend.
    assert [p["id"] for p in doc_vide["paragraphes"]] == ["p-2", "p-3"]


# --- Jalon A : ids de correction uniques entre phases -------------------------


def test_ids_dupliques_entre_phases_groupes_et_barre_distincts():
    """Deux phases émettent le même id « c-0001 » : après réassignation globale
    (analyse.py appelle renumeroter), le rendu produit 2 groupes distincts et
    2 entrées de barre latérale distinctes — avant le correctif, le dict
    `groupes` (clé = id) collait les deux corrections sur un même data-groupe."""
    forme = _corr("c-0001", "forme", 16, 22, "veille", "veillent")
    style = _corr("c-0001", "style", 16, 22, "veille", "veillaient")
    fusion = renumeroter([forme, style])
    assert len({c.id for c in fusion}) == 2  # ids réassignés uniques
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
            _corr("c-1", "forme", 16, 22, "veille", "veillent"),
            _corr("c-2", "style", 40, 50, "silencieux", "silencieux"),
        ],
        [_p()],
    )
    return etat


def test_projection_par_phase_n_affiche_que_sa_phase():
    """Chaque onglet ne montre QUE les corrections de sa phase : la projection
    filtre les `entrees` puis réutilise `preparer_document_depuis_etat` (logique
    unique)."""
    etat = _etat_deux_phases()

    doc_forme = rendu.preparer_document_depuis_etat(etat, "forme")
    segments = doc_forme["paragraphes"][0]["segments"]
    assert [s["type"] for s in segments] == ["texte", "forme", "texte"]
    assert all("mark-style" not in s["classes"] for s in segments)
    assert [i["phase"] for i in doc_forme["corrections_barre"]] == ["forme"]

    doc_style = rendu.preparer_document_depuis_etat(etat, "style")
    segments = doc_style["paragraphes"][0]["segments"]
    assert all(s["type"] == "texte" for s in segments)  # aucune Forme appliquée ici
    assert any("mark-style" in s["classes"] for s in segments)
    assert [i["phase"] for i in doc_style["corrections_barre"]] == ["style"]


def test_tout_reste_la_superposition_complete():
    """Régression : `preparer_document` (onglet « Tout ») reste inchangée —
    les deux phases restent superposées dans la même vue."""
    etat = _etat_deux_phases()
    doc = rendu.preparer_document_depuis_etat(etat)
    assert [i["phase"] for i in doc["corrections_barre"]] == ["forme", "style"]
    segments = doc["paragraphes"][0]["segments"]
    assert any(s["type"] == "forme" for s in segments)
    assert any("mark-style" in s["classes"] for s in segments if s["type"] == "texte")


def test_projection_phase_absente_rend_le_texte_neutre():
    """Aucune correction de la phase : la projection ne montre aucun marquage ;
    depuis FA3, le paragraphe reste EXPOSÉ (document complet) et reste compté
    comme masquable (décision 35)."""
    etat = _etat_deux_phases()
    doc = rendu.preparer_document_depuis_etat(etat, "technique")
    assert doc["corrections_barre"] == []
    assert [p["id"] for p in doc["paragraphes"]] == ["p-1"]
    assert doc["nb_masques"] == 1
    segments = doc["paragraphes"][0]["segments"]
    assert all("mark-style" not in s["classes"] for s in segments)


# --- Jalon FA3 : segmentation atomique + document complet -----------------------


def _segment_texte_couvrant(segments, a, b):
    """Retourne les segments texte dont l'union couvre [a, b) du texte courant."""
    position = 0
    couvrants = []
    for s in segments:
        longueur = len(s["ins"]) if s["type"] == "forme" else len(s.get("texte", ""))
        if s["type"] == "texte" and position < b and position + longueur > a:
            couvrants.append(s)
        position += longueur
    return couvrants


def test_fa3_segmentation_bornes_exactes_style():
    """RÉGRESSION FA3 (audit) : une correction Style au milieu d'un run unique
    ne doit marquer QUE ses bornes [6, 10) — jamais le run entier."""
    etat = reconstruction.etat_initial(
        [_corr("c-1", "style", 6, 10, "beta", "beta")],
        [ParagrapheRiche(id="p-1", runs=[RunFormat(texte="Alpha beta gamma.")])],
    )
    doc = rendu.preparer_document_depuis_etat(etat)
    segments = doc["paragraphes"][0]["segments"]
    avant = _segment_texte_couvrant(segments, 0, 6)
    sur = _segment_texte_couvrant(segments, 6, 10)
    apres = _segment_texte_couvrant(segments, 10, 15)
    assert avant and all("mark-style" not in s["classes"] for s in avant)
    assert sur and all("mark-style" in s["classes"] for s in sur)
    assert apres and all("mark-style" not in s["classes"] for s in apres)
    # le texte projeté est fidèle (aucune perte, aucun dédoublement)
    courant = "".join(s.get("texte", "") for s in segments)
    assert courant == "Alpha beta gamma."


def test_fa3_marques_disjointes_ne_fusionnent_pas():
    """Deux corrections disjointes (Style sur « Alpha », Technique sur « gamma »)
    produisent des zones marquées DISTINCTES avec des groupes distincts."""
    etat = reconstruction.etat_initial(
        [
            _corr("c-1", "style", 0, 5, "Alpha", "Alpha"),
            _corr("c-2", "technique", 11, 16, "gamma", "gamma"),
        ],
        [ParagrapheRiche(id="p-1", runs=[RunFormat(texte="Alpha beta gamma.")])],
    )
    doc = rendu.preparer_document_depuis_etat(etat)
    segments = doc["paragraphes"][0]["segments"]
    style = _segment_texte_couvrant(segments, 0, 5)
    technique = _segment_texte_couvrant(segments, 11, 16)
    assert style and all("mark-style" in s["classes"] for s in style)
    assert technique and all("mark-technique" in s["classes"] for s in technique)
    # aucun segment ne porte les deux marquages (zones disjointes)
    assert all("mark-technique" not in s["classes"] for s in style)
    assert all("mark-style" not in s["classes"] for s in technique)
    groupes = {s["groupe"] for s in style + technique if s["groupe"]}
    assert len(groupes) == 2


def test_fa3_multi_marquage_cumule_les_classes():
    """Deux corrections chevauchantes sur le même mot (Style + Technique) :
    le segment porte les classes CUMULÉES et un groupe parmi les couvrants."""
    etat = reconstruction.etat_initial(
        [
            _corr("c-1", "style", 6, 10, "beta", "beta"),
            _corr("c-2", "technique", 6, 10, "beta", "beta"),
        ],
        [ParagrapheRiche(id="p-1", runs=[RunFormat(texte="Alpha beta gamma.")])],
    )
    doc = rendu.preparer_document_depuis_etat(etat)
    segments = doc["paragraphes"][0]["segments"]
    sur = _segment_texte_couvrant(segments, 6, 10)
    assert sur
    classes = " ".join(s["classes"] for s in sur)
    assert "mark-style" in classes
    assert "mark-technique" in classes
    groupes = {s["groupe"] for s in sur if s["groupe"]}
    assert len(groupes) == 1  # un groupe de clic ; l'autre reste dans la barre
    assert doc["corrections_barre"][0]["groupe"] in groupes or \
        doc["corrections_barre"][1]["groupe"] in groupes


def test_fa3_document_complet_non_tronque_pour_le_toggle():
    """RÉGRESSION FA3 (audit) : `preparer_document` envoie TOUS les paragraphes
    du texte (les paragraphes propres ne sont plus retirés) — le toggle client
    « masquer » peut alors réafficher ce que le backend lui cachait."""
    p1 = ParagrapheRiche(id="p-1", runs=[RunFormat(texte=TEXTE)])
    p2 = ParagrapheRiche(id="p-2", runs=[RunFormat(texte="Rien à corriger ici.")])
    p3 = ParagrapheRiche(id="p-3", runs=[RunFormat(texte="Rien non plus.")])
    etat = reconstruction.etat_initial(
        [_corr("c-1", "forme", 16, 22, "veille", "veillent")], [p1, p2, p3]
    )
    doc = rendu.preparer_document_depuis_etat(etat)
    # TOUS les paragraphes sont exposés (3), avec le compteur de masquables
    assert [p["id"] for p in doc["paragraphes"]] == ["p-1", "p-2", "p-3"]
    assert doc["nb_masques"] == 2  # p-2 et p-3 sont éligibles au masquage
    # le paragraphe propre est bien un paragraphe neutre complet
    p2_segments = next(p for p in doc["paragraphes"] if p["id"] == "p-2")
    assert "".join(s["texte"] for s in p2_segments["segments"]) == "Rien à corriger ici."
    assert p2_segments["edite"] is False