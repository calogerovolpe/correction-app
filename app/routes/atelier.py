"""Écran E5 — atelier de relecture et workflow de fin de chapitre (jalon J2.5).

Modèle d'interaction (décisions de l'auteur, J2.5) :
- l'état courant du texte est matérialisé (`documents`, service `reconstruction`) ;
  « Valider la version actuelle » enregistre EXACTEMENT le texte affiché à
  l'écran, qu'il soit corrigé ou non ;
- les corrections peuvent se chevaucher visuellement (couches : Forme rouge,
  Style souligné pointillé bleu, Technique fond jaune) — cf. `rendu` ;
- l'Embellissement et les alternatives se demandent par SÉLECTION + clic droit ;
  un embellissement réévalue les corrections du paragraphe concerné ;
- la validation officielle n'existe que pour les Chapitres ; pour un
  Passage/Extrait, l'auteur est renvoyé vers E3 avec ses dernières
  configurations pré-cochées ;
- toute écriture dans `chapitres` est précédée d'un backup natif SQLite
  (spec §1.5/§9) — protection du manuscrit avec rotation sur `backups_max`.
"""

import asyncio
import hashlib
import json
from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import db
from app.config import settings
from app.llm import prompts as service_prompts
from app.models import CorrectionFusionnee, ReponseAlternatives, ReponseEmbellissement
from app.routes.web import TEMPLATES, _analyse, _TACHES
from app.services import analyse as service_analyse
from app.services import reconstruction, reconciliation as service_reconciliation
from app.services import rendu as service_rendu
from app.services import texte_riche as service_texte_riche
from app.services.normalisation import Paragraphe, extraire_titre_chapitre

router = APIRouter()

_MODELES_REEVALUATION = {
    "forme": lambda: settings.modele_forme,
    "style": lambda: settings.modele_style,
    "technique": lambda: settings.modele_technique,
}


# --- État courant (table `documents`) ----------------------------------------


async def _charger_fusion(identifiant: int) -> list[CorrectionFusionnee]:
    lignes = await db.interroger(
        "SELECT data_json FROM corrections WHERE analyse_id = ?", (identifiant,)
    )
    if not lignes:
        return []
    return [
        CorrectionFusionnee.model_validate(d)
        for d in json.loads(lignes[0]["data_json"])
    ]


async def _charger_etat(analyse) -> dict:
    lignes = await db.interroger(
        "SELECT document_json FROM documents WHERE analyse_id = ?", (analyse["id"],)
    )
    if lignes:
        return reconstruction.depuis_json(lignes[0]["document_json"])
    paragraphes = service_texte_riche.parser_document_riche(analyse["texte_source"])
    etat = reconstruction.etat_initial(await _charger_fusion(analyse["id"]), paragraphes)
    await db.executer(
        "INSERT INTO documents (analyse_id, document_json) VALUES (?, ?)",
        (analyse["id"], reconstruction.vers_json(etat)),
    )
    return etat


async def _sauver_etat(identifiant: int, etat: dict) -> None:
    await db.executer(
        "INSERT INTO documents (analyse_id, document_json) VALUES (?, ?) "
        "ON CONFLICT(analyse_id) DO UPDATE SET document_json = excluded.document_json",
        (identifiant, reconstruction.vers_json(etat)),
    )


def _contexte_resultat(analyse, etat, erreur=None) -> dict:
    document = service_rendu.preparer_document(
        etat["paragraphes"], etat["corrections"],
        etat.get("choix", {}), etat.get("modifies", []),
    )
    actives = [e for e in etat["corrections"] if e["etat"] == "active"]
    return {
        "analyse": analyse,
        "document": document,
        "nb_corrections": len(actives),
        "est_chapitre": (analyse["categorie"] == "chapitre"),
        "erreur_atelier": erreur,
    }


def _rendre_atelier(request: Request, analyse, etat, erreur=None):
    return TEMPLATES.TemplateResponse(
        request, "analyses/_atelier.html", _contexte_resultat(analyse, etat, erreur)
    )


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

    etat = await _charger_etat(analyse)
    return TEMPLATES.TemplateResponse(
        request, "analyses/resultat.html", _contexte_resultat(analyse, etat)
    )


@router.post("/analyses/{identifiant}/choix-forme")
async def choix_forme(
    request: Request,
    identifiant: int,
    correction_id: str = Form(...),
    decision: str = Form(...),
):
    """Accepte ('corrige', défaut) ou refuse ('original') une correction Forme :
    le texte courant est immédiatement reconstruit (splice + remappage)."""
    analyse = await _analyse(identifiant)
    if not analyse or analyse["statut"] != "terminee":
        return HTMLResponse("Analyse introuvable ou non terminée.", status_code=404)
    if decision not in ("corrige", "original"):
        return HTMLResponse("Décision inconnue.", status_code=400)
    etat = await _charger_etat(analyse)
    reconstruction.basculer_choix(etat, correction_id, decision)
    await _sauver_etat(identifiant, etat)
    return _rendre_atelier(request, analyse, etat)


@router.post("/analyses/{identifiant}/appliquer-alternative")
async def appliquer_alternative(
    request: Request,
    identifiant: int,
    paragraphe_id: str = Form(...),
    fragment: str = Form(...),
    texte: str = Form(...),
    contexte: str = Form(""),
):
    """Applique l'alternative choisie par l'auteur (clic droit sur sélection)."""
    analyse = await _analyse(identifiant)
    if not analyse or analyse["statut"] != "terminee":
        return HTMLResponse("Analyse introuvable ou non terminée.", status_code=404)
    etat = await _charger_etat(analyse)
    if not texte.strip():
        return _rendre_atelier(request, analyse, etat, "Le texte de remplacement est vide.")
    localisation = reconstruction.localiser(
        reconstruction.texte_paragraphe(etat, paragraphe_id), fragment, contexte
    )
    if localisation is None:
        return _rendre_atelier(
            request, analyse, etat,
            "Fragment introuvable dans le texte courant (zone déjà modifiée ?) — "
            "réévaluez le paragraphe avant de recommencer.",
        )
    debut, fin = localisation
    reconstruction.appliquer_modification(etat, paragraphe_id, debut, fin, texte)
    await _sauver_etat(identifiant, etat)
    return _rendre_atelier(request, analyse, etat)


async def _reevaluer_corrections(analyse, etat, paragraphe_id: str) -> list[CorrectionFusionnee]:
    """Relance les phases actives de l'analyse sur le SEUL paragraphe modifié
    (texte courant) — décision de l'auteur : les corrections de la zone sont
    réévaluées avec la modification. Liste vide valide (jamais une panne)."""
    texte = reconstruction.texte_paragraphe(etat, paragraphe_id)
    paragraphe = Paragraphe(id=paragraphe_id, texte=texte)
    options = json.loads(analyse["options_json"] or "{}")
    actives = service_analyse.phases_actives(analyse["categorie"] or "chapitre", options)
    client = service_analyse._client_llm()
    nouvelles: list[CorrectionFusionnee] = []
    compteur = 0
    for phase in actives:
        modele = _MODELES_REEVALUATION[phase]()
        if not modele:
            continue
        messages = service_prompts.prompt_phase_correction(
            phase, service_prompts.CONSIGNES_PHASES[phase], [paragraphe], settings.variante
        )
        sortie = await client.completer(
            modele, messages, temperature=settings.temperature_correction
        )
        for correction in service_reconciliation.extraire_corrections(sortie, phase):
            compteur += 1
            renommee = correction.model_copy(
                update={"id": f"c-r{compteur:04d}", "paragraphe_id": paragraphe_id}
            )
            reconciliee = service_reconciliation.reconcilier(renommee, paragraphe)
            if reconciliee is not None:
                nouvelles.append(CorrectionFusionnee(correction=reconciliee))
    return nouvelles


@router.post("/analyses/{identifiant}/reevaluer")
async def reevaluer(
    request: Request,
    identifiant: int,
    paragraphe_id: str = Form(...),
):
    """Réévaluation manuelle des corrections d'un paragraphe (bouton « ↻ »)."""
    analyse = await _analyse(identifiant)
    if not analyse or analyse["statut"] != "terminee":
        return HTMLResponse("Analyse introuvable ou non terminée.", status_code=404)
    etat = await _charger_etat(analyse)
    try:
        nouvelles = await _reevaluer_corrections(analyse, etat, paragraphe_id)
    except Exception as erreur:  # noqa: BLE001 — l'atelier ne doit jamais se bloquer
        return _rendre_atelier(
            request, analyse, etat,
            f"Réévaluation impossible (modèle indisponible ?) : {erreur}",
        )
    reconstruction.remplacer_corrections_paragraphe(etat, paragraphe_id, nouvelles)
    await _sauver_etat(identifiant, etat)
    return _rendre_atelier(request, analyse, etat)


@router.post("/analyses/{identifiant}/appliquer-embellissement")
async def appliquer_embellissement(
    request: Request,
    identifiant: int,
    paragraphe_id: str = Form(...),
    fragment: str = Form(...),
    texte: str = Form(...),
    contexte: str = Form(""),
):
    """Applique l'embellissement choisi, PUIS réévalue les corrections du
    paragraphe (décision de l'auteur : le texte change et les corrections de la
    zone sont réévaluées avec l'embellissement). Zéro surprise : si la
    réévaluation échoue, RIEN n'est appliqué (aucun état partiel)."""
    analyse = await _analyse(identifiant)
    if not analyse or analyse["statut"] != "terminee":
        return HTMLResponse("Analyse introuvable ou non terminée.", status_code=404)
    etat = await _charger_etat(analyse)
    if not texte.strip():
        return _rendre_atelier(request, analyse, etat, "Le texte embelli est vide.")
    localisation = reconstruction.localiser(
        reconstruction.texte_paragraphe(etat, paragraphe_id), fragment, contexte
    )
    if localisation is None:
        return _rendre_atelier(
            request, analyse, etat,
            "Fragment introuvable dans le texte courant (zone déjà modifiée ?) — "
            "réévaluez le paragraphe avant de recommencer.",
        )
    debut, fin = localisation
    reconstruction.appliquer_modification(etat, paragraphe_id, debut, fin, texte)
    try:
        nouvelles = await _reevaluer_corrections(analyse, etat, paragraphe_id)
    except Exception as erreur:  # noqa: BLE001 — aucun état partiel
        return _rendre_atelier(
            request, analyse, etat,
            f"Réévaluation impossible après embellissement : {erreur} — "
            "le texte n'a pas été modifié, réessayez.",
        )
    reconstruction.remplacer_corrections_paragraphe(etat, paragraphe_id, nouvelles)
    await _sauver_etat(identifiant, etat)
    return _rendre_atelier(request, analyse, etat)


# --- Suggestions à la demande (JSON, aucun état modifié) ----------------------


@router.post("/api/embellir")
async def api_embellir(demande: dict):
    """Propose une réécriture embellie du passage sélectionné, en tenant compte
    du contexte (paragraphe courant + paragraphe précédent). Aucun état modifié :
    l'auteur voit la proposition puis applique ou annule."""
    fragment = (demande.get("fragment") or "").strip()
    paragraphe_texte = demande.get("paragraphe_texte") or ""
    contexte = demande.get("contexte") or ""
    if not fragment:
        return {"erreur": "Sélectionnez d'abord un passage du texte."}
    messages = service_prompts.prompt_embellissement_selection(
        fragment, paragraphe_texte, contexte, settings.variante
    )
    client = service_analyse._client_llm()
    try:
        sortie = await client.completer(
            settings.modele_embellissement, messages,
            temperature=settings.temperature_embellissement,
        )
        reponse = ReponseEmbellissement.model_validate(
            json.loads(service_reconciliation.nettoyer_sortie_llm(sortie))
        )
        return {"texte": reponse.texte, "explication": reponse.explication}
    except Exception as erreur:  # noqa: BLE001 — message explicite, jamais de fantôme
        return {"erreur": f"Embellissement indisponible : {erreur}"}


@router.post("/api/alternatives")
async def api_alternatives(demande: dict):
    """Propose 3 à 5 alternatives (synonymes, champ lexical) cohérentes avec le
    contexte du mot/passage sélectionné (clic droit). Aucun état modifié."""
    fragment = (demande.get("fragment") or "").strip()
    paragraphe_texte = demande.get("paragraphe_texte") or ""
    if not fragment:
        return {"erreur": "Sélectionnez d'abord un mot ou un passage du texte."}
    messages = service_prompts.prompt_alternatives_a_la_demande(
        fragment=fragment,
        paragraphe_texte=paragraphe_texte,
        phase="style",
        mots_a_eviter=service_texte_riche.extraire_mots_frequents(paragraphe_texte),
        variante=settings.variante,
    )
    client = service_analyse._client_llm()
    try:
        sortie = await client.completer(settings.modele_style, messages, temperature=0.7)
        reponse = ReponseAlternatives.model_validate(
            json.loads(service_reconciliation.nettoyer_sortie_llm(sortie))
        )
        return {"alternatives": reponse.alternatives, "explication": reponse.explication}
    except Exception as erreur:  # noqa: BLE001 — message explicite, jamais de fantôme
        return {"erreur": f"Alternatives indisponibles : {erreur}"}


# --- Workflow de fin de chapitre (J2.5) ---------------------------------------


@router.post("/analyses/{identifiant}/nouvelle-version")
async def relancer_nouvelle_version(identifiant: int):
    """Soumet une NOUVELLE analyse dont le texte source est exactement le texte
    courant (le texte affiché, avec les choix et modifications de l'auteur)."""
    analyse = await _analyse(identifiant)
    if not analyse or analyse["statut"] != "terminee":
        return HTMLResponse("Analyse introuvable ou non terminée.", status_code=404)
    etat = await _charger_etat(analyse)
    nouveau_texte = service_texte_riche.serialiser_document_riche(etat["paragraphes"])
    # ATTENTION (piège J2.1) : db.executer retourne (lastrowid, rowcount) —
    # c'est bien lastrowid qu'il faut récupérer, sinon redirection vers /analyses/1.
    nouvel_id, _ = await db.executer(
        "INSERT INTO analyses (projet_id, texte_source, options_json) VALUES (?, ?, ?)",
        (analyse["projet_id"], nouveau_texte, analyse["options_json"]),
    )
    tache = asyncio.create_task(service_analyse.executer(nouvel_id))
    _TACHES.add(tache)
    tache.add_done_callback(_TACHES.discard)
    return RedirectResponse(f"/analyses/{nouvel_id}", status_code=303)


@router.post("/analyses/{identifiant}/valider")
async def valider_version_officielle(identifiant: int):
    """Valide officiellement le chapitre : enregistre dans `chapitres` le TEXTE
    AFFICHÉ au moment du clic (qu'il soit corrigé ou non), avec son hash
    SHA-256, après un backup natif SQLite ; « dernier validé gagne » fait
    avancer la chaîne N+1. Réservé aux Chapitres (Passage/Extrait : 400)."""
    analyse = await _analyse(identifiant)
    if not analyse:
        return HTMLResponse("Analyse introuvable.", status_code=404)
    if analyse["statut"] != "terminee":
        return HTMLResponse("Analyse non terminée.", status_code=400)
    if analyse["categorie"] != "chapitre":
        return HTMLResponse(
            "Seul un Chapitre peut être validé officiellement. "
            "Pour un Passage ou un Extrait, soumettez un autre texte.",
            status_code=400,
        )

    etat = await _charger_etat(analyse)
    texte_complet = "\n".join(reconstruction.textes_plats(etat))
    empreinte = hashlib.sha256(texte_complet.encode("utf-8")).hexdigest()

    # Backup natif AVANT toute écriture narrative (spec §1.5/§9) + rotation
    horodatage = datetime.now().strftime("%Y%m%d-%H%M%S")
    await db.sauvegarder(settings.data_dir / "backups" / f"backup-{horodatage}.sqlite3")
    await db.purger_backups(settings.backups_max)

    # Numéro du chapitre : priorité aux options choisies lors de la soumission
    options = json.loads(analyse["options_json"] or "{}")
    num_option = options.get("numero_chapitre")
    if num_option is not None:
        numero = int(num_option)
        titre_texte = "Prologue" if numero == 0 else f"Chapitre {numero}"
    else:
        titre_info = extraire_titre_chapitre(texte_complet)
        numero = int(titre_info[0]) if titre_info else 1
        titre_texte = titre_info[1] if titre_info else f"Chapitre {numero}"

    await db.executer(
        "INSERT OR REPLACE INTO chapitres (projet_id, numero, texte, hash) VALUES (?, ?, ?, ?)",
        (analyse["projet_id"], numero, texte_complet, empreinte),
    )
    # « Dernier validé gagne » : le numéro validé devient la référence (spec §5.2)
    await db.executer(
        "UPDATE projets SET current_chapter_num = ?, last_chapter_title = ?, "
        "chain_status = 'ok' WHERE projet_id = ?",
        (numero, titre_texte, analyse["projet_id"]),
    )
    return RedirectResponse(f"/analyses/{identifiant}", status_code=303)