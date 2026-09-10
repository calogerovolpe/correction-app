"""Catalogue des modèles texte de l'API Mistral — sélection par l'auteur (FA6).

L'auteur choisit l'IA qui corrigera son texte AU MOMENT de la soumission (E3),
parmi les modèles TEXTE officiels de l'API Mistral supportant les Custom
Structured Outputs (FA5). Le modèle choisi s'applique à TOUTES les phases de
l'analyse ; sans choix (ou choix inconnu), la configuration `.env` par phase
(`APP_MODELE_*`) reste maîtresse — repli transparent, jamais de blocage.

Les clés `id` sont des identifiants réels de l'API Mistral ; `libelle`,
`badge` et `description` sont destinés à l'UI (persona auteur non développeur :
vocabulaire simple, aucun jargon)."""

from app.config import settings

MODELES_TEXTE: list[dict[str, str | None]] = [
    {
        "id": "mistral-small-latest",
        "libelle": "Mistral Small",
        "badge": "Recommandé",
        "description": (
            "Le meilleur équilibre : correction fine, rapide et économique — "
            "idéal pour la relecture courante de vos chapitres."
        ),
    },
    {
        "id": "mistral-large-latest",
        "libelle": "Mistral Large",
        "badge": "Haute précision",
        "description": (
            "Le plus rigoureux : raisonnement approfondi pour les chapitres "
            "denses (plus lent et plus coûteux)."
        ),
    },
    {
        "id": "open-mistral-nemo",
        "libelle": "Mistral Nemo",
        "badge": "Rapide",
        "description": (
            "Correction véloce pour les passages courts et les itérations "
            "nombreuses."
        ),
    },
    {
        "id": "ministral-8b-latest",
        "libelle": "Ministral 8B",
        "badge": "Compact",
        "description": (
            "Modèle léger et réactif, pour un premier passage rapide."
        ),
    },
]

_IDS_AUTORISES = {m["id"] for m in MODELES_TEXTE}


def modele_autorise(identifiant: str | None) -> bool:
    """True si l'identifiant appartient au catalogue des modèles texte Mistral."""
    return bool(identifiant) and identifiant in _IDS_AUTORISES


def modele_effectif(identifiant: str | None) -> str | None:
    """Modèle à mémoriser dans les options de l'analyse : l'identifiant choisi
    s'il figure au catalogue, sinon None (la configuration `.env` par phase
    reste maîtresse — repli transparent, jamais de blocage)."""
    return identifiant if modele_autorise(identifiant) else None


def modele_par_defaut() -> str:
    """Modèle pré-sélectionné dans E3 : la configuration actuelle de Forme
    (`.env`), sinon le modèle recommandé du catalogue."""
    return settings.modele_forme or str(MODELES_TEXTE[0]["id"])