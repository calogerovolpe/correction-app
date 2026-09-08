"""API JSON — /api/v1 (jalon F1 : Accueil & projets E1).

Réutilise les services purs et l'accès SQL existants (`app.db`) — aucune
logique métier dupliquée. Les routes Jinja2 de `app.routes.web` restent
conservées jusqu'à la bascule (F5) ; ce routeur est la cible du frontend
Svelte.

Comportement métier (spec §8.2-E1, §11 décisions 16 et 37) :
- création (le premier projet d'un espace vierge devient automatiquement actif) ;
- activation par UPSERT du pointeur `parametres.projet_actif` (un seul actif) ;
- suppression totale en cascade, projet actif protégé (le trigger SQL
  `trg_projet_actif_restrict` reste la garantie ultime derrière le 409).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.routes.web import _nouvel_id, _projet_actif_id

router = APIRouter(prefix="/api/v1")


class TitreProjet(BaseModel):
    titre: str = Field(min_length=1, max_length=200)


class Projet(BaseModel):
    projet_id: str
    titre: str
    actif: bool
    chain_status: str
    current_chapter_num: int | None
    last_chapter_title: str | None
    created_at: str


class ListeProjets(BaseModel):
    projets: list[Projet]


class AnalyseLigne(BaseModel):
    id: int
    statut: str
    categorie: str | None
    extrait: str
    cree_a: str


class ListeAnalyses(BaseModel):
    analyses: list[AnalyseLigne]


def _serialiser_projet(ligne: dict, actif_id: str | None) -> Projet:
    """Sérialise une ligne `projets` en réponse API (drapeau `actif` calculé)."""
    return Projet(
        projet_id=ligne["projet_id"],
        titre=ligne["titre"],
        actif=ligne["projet_id"] == actif_id,
        chain_status=ligne["chain_status"],
        current_chapter_num=ligne["current_chapter_num"],
        last_chapter_title=ligne["last_chapter_title"],
        created_at=ligne["created_at"],
    )


@router.get("/projets", response_model=ListeProjets)
async def lister_projets() -> ListeProjets:
    """Liste des projets (tri : plus récents d'abord), avec drapeau `actif`."""
    actif_id = await _projet_actif_id()
    lignes = await db.interroger(
        "SELECT * FROM projets ORDER BY created_at DESC, projet_id DESC"
    )
    return ListeProjets(projets=[_serialiser_projet(l, actif_id) for l in lignes])


@router.post("/projets", response_model=Projet, status_code=201)
async def creer_projet(payload: TitreProjet) -> Projet:
    """Crée un projet (titre obligatoire, non vide). Le premier projet d'un
    espace vierge devient automatiquement le projet actif (spec §11 déc. 16)."""
    titre = payload.titre.strip()
    if not titre:
        raise HTTPException(status_code=400, detail="Le titre du projet est vide.")
    projet_id = _nouvel_id()
    await db.executer(
        "INSERT INTO projets (projet_id, titre) VALUES (?, ?)", (projet_id, titre)
    )
    if await _projet_actif_id() is None:
        await db.executer(
            "INSERT INTO parametres (cle, valeur) VALUES ('projet_actif', ?)",
            (projet_id,),
        )
    actif_id = await _projet_actif_id()
    lignes = await db.interroger(
        "SELECT * FROM projets WHERE projet_id = ?", (projet_id,)
    )
    return _serialiser_projet(lignes[0], actif_id)


@router.post("/projets/{projet_id}/activer", status_code=204)
async def activer_projet(projet_id: str) -> None:
    """Active un projet : UPSERT du pointeur `parametres.projet_actif`
    (un seul projet actif à la fois)."""
    lignes = await db.interroger(
        "SELECT 1 FROM projets WHERE projet_id = ?", (projet_id,)
    )
    if not lignes:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    await db.executer(
        "INSERT INTO parametres (cle, valeur) VALUES ('projet_actif', ?) "
        "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
        (projet_id,),
    )


@router.delete("/projets/{projet_id}", status_code=204)
async def supprimer_projet(projet_id: str) -> None:
    """Supprime un projet non actif ; la suppression totale en cascade est
    portée par le schéma (ON DELETE CASCADE sur toutes les tables filles).
    Projet actif : refus explicite 409 en amont du trigger SQL."""
    lignes = await db.interroger(
        "SELECT 1 FROM projets WHERE projet_id = ?", (projet_id,)
    )
    if not lignes:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    if projet_id == await _projet_actif_id():
        raise HTTPException(
            status_code=409,
            detail="Le projet actif ne peut pas être supprimé — activez d'abord un autre projet.",
        )
    await db.executer("DELETE FROM projets WHERE projet_id = ?", (projet_id,))


@router.get("/analyses", response_model=ListeAnalyses)
async def analyses_recentes() -> ListeAnalyses:
    """Analyses récentes (10 dernières, lecture seule) pour l'accueil E1."""
    lignes = await db.interroger(
        "SELECT id, statut, categorie, substr(texte_source, 1, 60) AS extrait, cree_a "
        "FROM analyses ORDER BY id DESC LIMIT 10"
    )
    return ListeAnalyses(analyses=[AnalyseLigne(**l) for l in lignes])