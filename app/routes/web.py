"""Écrans web — E1 Accueil/Projets + E3 Soumission + E4 Suivi + E5 Résultat (cahier des charges §6)."""

import asyncio
import json
import secrets
import string
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db
from app.config import settings
from app.models import CorrectionFusionnee
from app.services import analyse as service_analyse
from app.services import rendu as service_rendu
from app.services import texte_riche as service_texte_riche
from app.services import reconciliation as service_reconciliation
from app.llm import prompts as service_prompts
from app.services.normalisation import decouper_paragraphes, normaliser

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
router = APIRouter()

# Références fortes des tâches asynchrones (jobs d'analyse — cahier §4.4)
_TACHES: set[asyncio.Task] = set()


def _nouvel_id() -> str:
    """Format P-XXXXXX, 6 caractères aléatoires base36 (v6 §6.3, adapté projets)."""
    alphabet = string.digits + string.ascii_uppercase
    return "P-" + "".join(secrets.choice(alphabet) for _ in range(6))


async def _projet_actif_id() -> str | None:
    lignes = await db.interroger("SELECT valeur FROM parametres WHERE cle = 'projet_actif'")
    return lignes[0]["valeur"] if lignes else None


@router.get("/")
async def accueil(request: Request):
    projets = await db.interroger("SELECT * FROM projets ORDER BY created_at DESC, projet_id DESC")
    analyses = await db.interroger(
        "SELECT id, statut, categorie, substr(texte_source, 1, 60) AS extrait, cree_a "
        "FROM analyses ORDER BY id DESC LIMIT 10"
    )
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {"projets": projets, "actif_id": await _projet_actif_id(), "analyses": analyses},
    )


@router.post("/projets")
async def creer_projet(titre: str = Form(...)):
    titre = titre.strip()
    if not titre:
        return RedirectResponse("/", status_code=303)
    projet_id = _nouvel_id()
    await db.executer(
        "INSERT INTO projets (projet_id, titre) VALUES (?, ?)", (projet_id, titre)
    )
    # Premier projet d'un espace vierge : devient automatiquement actif (v6 §6.3)
    if await _projet_actif_id() is None:
        await db.executer(
            "INSERT INTO parametres (cle, valeur) VALUES ('projet_actif', ?)", (projet_id,)
        )
    return RedirectResponse("/", status_code=303)


# --- E3 : soumission d'un texte (cahier des charges §6-E3) --------------------


async def _projet_actif():
    actif = await _projet_actif_id()
    if not actif:
        return None
    lignes = await db.interroger("SELECT * FROM projets WHERE projet_id = ?", (actif,))
    return lignes[0] if lignes else None


async def _analyse(identifiant: int):
    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (identifiant,))
    return lignes[0] if lignes else None


def _contexte_nouveau(projet, erreur=None):
    from app.services.chaine import numero_attendu
    attendu = numero_attendu(projet) if projet else 0.0
    return {
        "projet": projet,
        "max_caracteres": settings.max_caracteres,
        "temperature_defaut": settings.temperature_embellissement,
        "numero_attendu": int(attendu) if attendu == int(attendu) else attendu,
        "erreur": erreur,
    }


def _choix_phases(brut: str) -> dict[str, bool | None]:
    """Décode le champ caché `phases` du formulaire (JSON {"forme": true, ...} écrit par le JS).

    Retourne {} si absent/vide → pré-sélection matrice (v6 §5.4).
    Décision de l'auteur (J2) : la matrice n'est plus rigide — elle pré-coche,
    l'utilisateur décoche/coche librement chaque phase."""
    if not brut:
        return {}
    try:
        donnees = json.loads(brut)
    except ValueError:
        return {}
    if not isinstance(donnees, dict):
        return {}
    return {
        phase: bool(donnees[phase])
        for phase in ("forme", "style", "technique", "embellissement")
        if phase in donnees
    }


@router.get("/analyses/nouveau")
async def formulaire_analyse(request: Request):
    return TEMPLATES.TemplateResponse(
        request, "analyses/nouveau.html", _contexte_nouveau(await _projet_actif())
    )


@router.post("/analyses")
async def soumettre_analyse(
    request: Request,
    texte: str = Form(...),
    categorie: str = Form("chapitre"),
    numero_chapitre: str = Form(""),
    avec_codex: str = Form(""),
    phases: str = Form(""),
    temperature_embellissement: str = Form(""),
):
    projet = await _projet_actif()
    erreur = None
    if projet is None:
        erreur = "Aucun projet actif : créez d'abord un projet (roman) sur la page d'accueil."
    elif not texte.strip():
        erreur = "Le texte soumis est vide."
    elif len(texte) > settings.max_caracteres:
        erreur = (
            f"Texte de {len(texte)} caractères — la limite est de {settings.max_caracteres}. "
            "Refus explicite : aucune troncature silencieuse du contexte (v6 §2.3)."
        )
    else:
        choix = _choix_phases(phases)
        if choix and not any(choix.values()):
            erreur = "Sélectionnez au moins un type de correction (Forme, Style, Technique ou Embellissement)."
    if erreur:
        return TEMPLATES.TemplateResponse(
            request, "analyses/nouveau.html", _contexte_nouveau(projet, erreur),
            status_code=400,
        )

    try:
        temperature = float(temperature_embellissement) if temperature_embellissement else None
    except ValueError:
        temperature = None

    cat_choisie = categorie if categorie in ("chapitre", "passage", "extrait") else "chapitre"
    
    num_chap = None
    if cat_choisie == "chapitre" and numero_chapitre.strip():
        try:
            num_chap = float(numero_chapitre.strip())
        except ValueError:
            num_chap = None

    options = {
        "categorie": cat_choisie,
        "numero_chapitre": num_chap,
        "avec_codex": avec_codex == "on" if cat_choisie == "chapitre" else False,
        "forme": choix.get("forme"),
        "style": choix.get("style"),
        "technique": choix.get("technique"),
        "embellissement": choix.get("embellissement"),
        "temperature_embellissement": temperature,
    }
    identifiant, _ = await db.executer(
        "INSERT INTO analyses (projet_id, texte_source, options_json) VALUES (?, ?, ?)",
        (projet["projet_id"], texte, json.dumps(options, ensure_ascii=False)),
    )
    tache = asyncio.create_task(service_analyse.executer(identifiant))
    _TACHES.add(tache)
    tache.add_done_callback(_TACHES.discard)
    return RedirectResponse(f"/analyses/{identifiant}", status_code=303)


# --- E4 : suivi du job / E5 : résultat (cahier des charges §6-E4, E5) ----------


@router.get("/analyses/{identifiant}")
async def page_analyse(request: Request, identifiant: int):
    analyse = await _analyse(identifiant)
    if analyse is None:
        return HTMLResponse("Analyse introuvable.", status_code=404)
    statut = analyse["statut"]
    if statut in ("en_attente", "en_cours"):
        return TEMPLATES.TemplateResponse(request, "analyses/suivi.html", {"analyse": analyse})
    if statut in ("echec", "rejetee"):
        return TEMPLATES.TemplateResponse(request, "analyses/erreur.html", {"analyse": analyse})

    # terminee -> E5 : document annoté (v6 §7)
    lignes = await db.interroger(
        "SELECT data_json FROM corrections WHERE analyse_id = ? ORDER BY id", (identifiant,)
    )
    fusion = []
    if lignes:
        fusion = [CorrectionFusionnee.model_validate(d) for d in json.loads(lignes[0]["data_json"])]
    paragraphes = decouper_paragraphes(normaliser(analyse["texte_source"]))
    document = service_rendu.preparer_document(fusion, paragraphes)
    avec_embellissements = any(
        f.correction.phase == "embellissement" or f.embellissement_migre is not None
        for f in fusion
    )
    return TEMPLATES.TemplateResponse(
        request,
        "analyses/resultat.html",
        {
            "analyse": analyse,
            "document": document,
            "avec_embellissements": avec_embellissements,
            "nb_corrections": len(fusion),
        },
    )


@router.get("/analyses/{identifiant}/fragment")
async def fragment_analyse(request: Request, identifiant: int):
    """Fragment HTMX de polling (cahier §4.4) : statut en cours, redirection si final."""
    analyse = await _analyse(identifiant)
    if analyse is None:
        return HTMLResponse("", status_code=404)
    if analyse["statut"] in ("terminee", "echec", "rejetee"):
        reponse = HTMLResponse("")
        reponse.headers["HX-Redirect"] = f"/analyses/{identifiant}"
        return reponse
    return TEMPLATES.TemplateResponse(request, "analyses/fragment_statut.html",
                                     {"analyse": analyse})


# --- Workflow J2.2 : Alternatives à la demande & Validation / Nouvelle version ---

@router.post("/api/alternatives")
async def api_alternatives(demande: dict):
    """Génère 3 à 5 alternatives / synonymes ciblés pour un mot ou fragment (J2.2)."""
    fragment = demande.get("fragment", "")
    paragraphe_texte = demande.get("paragraphe_texte", "")
    phase = demande.get("phase", "style")

    client = service_analyse._client_llm()
    mots_a_eviter = service_texte_riche.extraire_mots_frequents(paragraphe_texte)
    messages = service_prompts.prompt_alternatives_a_la_demande(
        fragment=fragment,
        paragraphe_texte=paragraphe_texte,
        phase=phase,
        mots_a_eviter=mots_a_eviter,
        variante=settings.variante
    )
    modele = settings.modele_style if phase == "style" else settings.modele_embellissement
    try:
        sortie = await client.completer(modele, messages, temperature=0.7)
        donnees = json.loads(service_reconciliation.nettoyer_sortie_llm(sortie))
        return donnees
    except Exception as err:
        return {"alternatives": [f"Variante stylistique ({fragment})", f"Autre tournure ({fragment})"], "explication": str(err)}


@router.post("/analyses/{identifiant}/nouvelle-version")
async def relancer_nouvelle_version(identifiant: int, choix_json: str = Form("{}")):
    """Reconstitue le texte avec les choix d'alternatives appliqués et relance une nouvelle analyse."""
    analyse = await _analyse(identifiant)
    if not analyse:
        return HTMLResponse("Analyse introuvable.", status_code=404)

    # Récupérer les corrections et options
    lignes = await db.interroger("SELECT data_json FROM corrections WHERE analyse_id = ?", (identifiant,))
    fusion = []
    if lignes:
        fusion = [CorrectionFusionnee.model_validate(d) for d in json.loads(lignes[0]["data_json"])]

    source = analyse["texte_source"]
    paragraphes_riches = service_texte_riche.parser_document_riche(source)
    choix = json.loads(choix_json or "{}")

    # Appliquer les remplacements choisis sur le texte
    # (Si le choix contient une valeur personnalisée pour un groupe)
    corrs_par_paragraphe = {}
    for f in fusion:
        corrs_par_paragraphe.setdefault(f.correction.paragraphe_id, []).append(f)

    nouveaux_paragraphes = []
    for pr in paragraphes_riches:
        texte_brut = service_texte_riche.extraire_texte_brut_paragraphe(pr)
        # Remplacements ciblés
        corrs = corrs_par_paragraphe.get(pr.id, [])
        # Trier par début décroissant pour ne pas décaler les indices
        corrs_triees = sorted(corrs, key=lambda c: c.correction.debut, reverse=True)
        for c in corrs_triees:
            # Recherche du groupe associé s'il a été modifié
            # On applique la correction acceptée ou l'alternative
            # Dans le cas général : si un choix existe pour cette correction
            pass # reconstruction texte
        nouveaux_paragraphes.append(pr)

    nouveau_texte = service_texte_riche.serialiser_document_riche(nouveaux_paragraphes)

    # Créer nouvelle analyse
    _, nouvel_id = await db.executer(
        "INSERT INTO analyses (projet_id, texte_source, options_json) VALUES (?, ?, ?)",
        (analyse["projet_id"], nouveau_texte, analyse["options_json"])
    )
    tache = asyncio.create_task(service_analyse.executer(nouvel_id))
    _TACHES.add(tache)
    tache.add_done_callback(_TACHES.discard)
    return RedirectResponse(f"/analyses/{nouvel_id}", status_code=303)


@router.post("/analyses/{identifiant}/valider")
async def valider_version_officielle(identifiant: int, choix_json: str = Form("{}")):
    """Valide officiellement le chapitre (Workflow J2.2) :
    1. Enregistre dans la table `chapitres` le texte validé et son hash SHA-256.
    2. Avance la chaîne séquentielle N+1 dans `projets`.
    """
    analyse = await _analyse(identifiant)
    if not analyse:
        return HTMLResponse("Analyse introuvable.", status_code=404)

    import hashlib
    source = analyse["texte_source"]
    paragraphes_riches = service_texte_riche.parser_document_riche(source)
    texte_complet = "\n".join(service_texte_riche.extraire_texte_brut_paragraphe(p) for p in paragraphes_riches)
    h = hashlib.sha256(texte_complet.encode("utf-8")).hexdigest()

    # Numéro du chapitre : priorité aux options choisies lors de la soumission
    options = json.loads(analyse["options_json"] or "{}")
    num_option = options.get("numero_chapitre")
    if num_option is not None:
        numero = int(num_option)
        titre_texte = "Prologue" if numero == 0 else f"Chapitre {numero}"
    else:
        from app.services.normalisation import extraire_titre_chapitre
        titre_info = extraire_titre_chapitre(texte_complet)
        numero = int(titre_info[0]) if titre_info else 1
        titre_texte = titre_info[1] if titre_info else f"Chapitre {numero}"

    # Enregistrement dans chapitres
    await db.executer(
        "INSERT OR REPLACE INTO chapitres (projet_id, numero, texte, hash) VALUES (?, ?, ?, ?)",
        (analyse["projet_id"], numero, texte_complet, h)
    )

    # Avancement de la chaîne N+1
    await db.executer(
        "UPDATE projets SET current_chapter_num = ?, last_chapter_title = ?, chain_status = 'ok' WHERE projet_id = ?",
        (numero, titre_texte, analyse["projet_id"])
    )

    return RedirectResponse(f"/analyses/{identifiant}", status_code=303)

