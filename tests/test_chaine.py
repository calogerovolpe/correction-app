"""Tests de la chaîne séquentielle déclarative et numéro attendu (J2.3)."""

from app.services import chaine


def _projet(courant=None, statut="vierge"):
    return {
        "projet_id": "P-TEST",
        "titre": "Roman test",
        "current_chapter_num": courant,
        "chain_status": statut,
    }


def test_numero_attendu_vierge():
    # Session vierge -> Prologue (0.0) attendu par défaut
    assert chaine.numero_attendu(_projet(None)) == 0.0


def test_numero_attendu_apres_prologue():
    # Après Prologue (0) -> Chapitre 1.0 attendu
    assert chaine.numero_attendu(_projet(0)) == 1.0


def test_numero_attendu_apres_chapitre_3():
    # Après Chapitre 3 -> Chapitre 4.0 attendu
    assert chaine.numero_attendu(_projet(3)) == 4.0
