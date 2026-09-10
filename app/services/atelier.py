"""Orchestration de l'atelier E5 — spec §8.2 (jalons J2.5 → R2 → F3).

Logique métier PARTAGÉE entre les routes Jinja2 (`app/routes/atelier.py`,
conservées jusqu'à la bascule F5) et l'API JSON `/api/v1`
(`app/routes/api.py`, cible du frontend Svelte) : AUCUNE logique métier
dupliquée (systemPatterns n°1). Ce module orchestre les services purs
(`reconstruction`, `rendu`, `reconciliation`, `texte_riche`) et l'accès SQL
(`app.db`) autour de l'état `documents` (base immuable + annotations, R2) :

- le « texte affiché » est la PROJECTION calculée (base + patches manuels +
  Forme acceptées) ; refuser une Forme = un FILTRE, jamais un remappage ;
- Style/Technique marquent SANS réécrire (fond jaune Technique, pointillés
  Style) ; l'Embellissement/les alternatives se demandent à la demande ;
- un embellissement applique le patch PUIS réévalue les corrections du
  paragraphe — aucun état partiel si la réévaluation échoue ;
- la validation officielle (Chapitres uniquement) enregistre EXACTEMENT le
  texte affiché, précédée d'un backup natif SQLite (spec §1.5/§9).

Approche délibérée : chaque fonction qui mute l'état le fait sur l'état
chargé puis le sauvegarde via `sauver_etat` ; les erreurs métier lèvent
`ErreurAtelier` (message affichable), que les couches HTTP traduisent
(HTMLResponse côté Jinja2, HTTPException côté JSON).
"""

import asyncio
import copy
import hashlib
import json
import logging
import re
from datetime import datetime

from app import db
from app.config import settings
from app.llm import prompts as service_prompts
from app.models import (
    Correction,
    ReponseAlternatives,
    ReponseCorrections,
    ReponseEmbellissement,
)
from app.routes.web import _TACHES
from app.services import analyse as service_analyse
from app.services import reconstruction
from app.services import reconciliation as service_reconciliation
from app.services import rendu as service_rendu
from app.services import texte_riche as service_texte_riche
from app.services.normalisation import Paragraphe, extraire_titre_chapitre

JOURNAL = logging.getLogger("correction.atelier")

_MODELE_REEVALUATION = {
    "forme": lambda: settings.modele_forme,
    "style": lambda: settings.modele_style,
    "technique": lambda: settings.modele_technique,
}

# Onglets hybrides (R1-a) : « tout » = superposition, sinon la projection d'une phase.
_ONGLETS = ("forme", "style", "technique", "embellissement")


class ErreurAtelier(Exception):
    """Erreur métier de l'atelier portant un message affichable, et un statut
    HTTP suggéré (défaut 400) pour les couches d'interface."""

    def __init__(self, message: str, statut: int = 400):
        super().__init__(message)
        self.statut = statut


def onglet_valide(onglet: str | None) -> str:
    """Normalise un nom d'onglet (« tout » par défaut, phase sinon)."""
    return onglet if onglet in _ONGLETS else "tout"


# --- État courant (table `documents`) ----------------------------------------


async def charger_corrections(identifiant: int) -> list[Correction]:
    """Lit `corrections.data_json` et l'aplatit en `list[Correction]`.

    Deux formats acceptés (FA3 — rétrocompatibilité constatée en production) :
    - dict PAR PHASE (R1-b, norme actuelle) : `{"forme": [...], "style": [...],
      "technique": [...]}` ;
    - liste PLATE (analyses d'avant R1-b encore en base) : `[{...}, {...}]` —
      un chargement naïf levait `AttributeError: 'list' object has no attribute
      'values'` et une Erreur 500 à l'ouverture de l'atelier."""
    lignes = await db.interroger(
        "SELECT data_json FROM corrections WHERE analyse_id = ?", (identifiant,)
    )
    if not lignes:
        return []
    donnees = json.loads(lignes[0]["data_json"])
    if isinstance(donnees, list):
        return [Correction.model_validate(d) for d in donnees]
    return [
        Correction.model_validate(d)
        for corrections in donnees.values()
        for d in corrections
    ]


async def charger_etat(analyse) -> dict:
    """État courant de l'atelier (`documents`) avec migration R2 à la volée si
    un état antérieur (texte mutable) est rencontré."""
    lignes = await db.interroger(
        "SELECT document_json FROM documents WHERE analyse_id = ?", (analyse["id"],)
    )
    if lignes:
        donnees = json.loads(lignes[0]["document_json"])
        if not reconstruction.est_ancien_format(donnees):
            return reconstruction.depuis_json(lignes[0]["document_json"])
        # Migration R2 : base + corrections reconstruites depuis les sources,
        # choix préservés par id, modifications manuelles abandonnées.
        base = service_texte_riche.parser_document_riche(analyse["texte_source"])
        return reconstruction.migrer_ancien_format(
            donnees, base, await charger_corrections(analyse["id"])
        )
    paragraphes = service_texte_riche.parser_document_riche(analyse["texte_source"])
    etat = reconstruction.etat_initial(
        await charger_corrections(analyse["id"]), paragraphes
    )
    await db.executer(
        "INSERT INTO documents (analyse_id, document_json) VALUES (?, ?)",
        (analyse["id"], reconstruction.vers_json(etat)),
    )
    return etat


async def sauver_etat(identifiant: int, etat: dict) -> None:
    """Persiste l'état courant (UPSERT de `documents`).

    FA6 — cohérence transactionnelle : la clé `revision` est incrémentée à
    CHAQUE sauvegarde. Le frontend la reçoit dans le contrat de l'atelier et
    la retransmet avec ses mutations : une requête qui porte une révision
    périmée est refusée (409) au lieu d'écraser silencieusement l'action d'un
    autre onglet (contrôle de concurrence optimiste — CAS)."""
    etat["revision"] = int(etat.get("revision", 1)) + 1
    await db.executer(
        "INSERT INTO documents (analyse_id, document_json) VALUES (?, ?) "
        "ON CONFLICT(analyse_id) DO UPDATE SET document_json = excluded.document_json",
        (identifiant, reconstruction.vers_json(etat)),
    )


def verifier_revision(etat: dict, revision: int | None) -> None:
    """FA6 — contrôle de concurrence optimiste : si le client transmet une
    révision qui ne correspond plus à l'état courant, la mutation est refusée
    (409) AVANT toute modification — l'auteur recharge l'atelier au lieu de
    perdre une action dans un écrasement silencieux. `revision=None` (routes
    Jinja2, appels non révisés) ne vérifie rien : compatibilité conservée."""
    if revision is None:
        return
    courante = int(etat.get("revision", 1))
    if revision != courante:
        raise ErreurAtelier(
            "L'atelier a été modifié dans un autre onglet ou une autre session "
            "(révision périmée). Rechargez la page pour récupérer l'état à jour "
            "avant de réessayer.",
            statut=409,
        )


def contexte_resultat(analyse, etat: dict, erreur=None, onglet="tout") -> dict:
    """Document annoté (projection de l'onglet) + métadonnées de l'atelier.
    Contrat partagé par le template Jinja2 (jusqu'à F5) et l'API JSON F3."""
    onglet = onglet_valide(onglet)
    document = service_rendu.preparer_document_depuis_etat(etat, onglet)
    actives = [e for e in etat["corrections"] if e["etat"] == "active"]
    compteurs: dict[str, int] = {}
    for entree in actives:
        phase = entree["correction"].phase
        compteurs[phase] = compteurs.get(phase, 0) + 1
    return {
        "analyse": analyse,
        "document": document,
        "nb_corrections": len(actives),
        "compteurs": compteurs,
        "est_chapitre": (analyse["categorie"] == "chapitre"),
        "erreur_atelier": erreur,
        "onglet": onglet,
        # Onglet « Embellissement » affiché seulement si une correction de cette
        # phase existe (calculé sur l'état COMPLET : la projection d'un onglet
        # filtrerait sinon la barre et ferait disparaître l'onglet).
        "a_embellissement": any(
            e["correction"].phase == "embellissement" for e in etat["corrections"]
        ),
    }


# --- Actions de l'atelier -----------------------------------------------------


async def choisir_forme(
    analyse, etat: dict, correction_id: str, decision: str, revision: int | None = None
) -> None:
    """Accepte ('corrige', défaut) ou refuse ('original') une correction Forme :
    un simple FILTRE (R2) — aucun remappage, la projection se recalcule.
    FA6 : `revision` (optionnel) — CAS, 409 si l'état a changé ailleurs."""
    verifier_revision(etat, revision)
    if decision not in ("corrige", "original"):
        raise ErreurAtelier("Décision inconnue.")
    if not reconstruction.basculer_choix(etat, correction_id, decision):
        raise ErreurAtelier(
            "Correction inconnue ou non modifiable (Forme active requise)."
        )
    await sauver_etat(analyse["id"], etat)


async def _appliquer_patch(
    etat: dict, paragraphe_id: str, fragment: str, texte: str, contexte: str
) -> None:
    """Ancre la sélection sur la base et l'applique comme patch manuel, SANS
    sauvegarder (la sauvegarde appartient à l'action appelante — l'embellissement
    sauve seulement après une réévaluation RÉUSSIE : aucun état partiel)."""
    if not texte.strip():
        raise ErreurAtelier("Le texte de remplacement est vide.")
    localisation = reconstruction.localiser(
        reconstruction.texte_paragraphe(etat, paragraphe_id), fragment, contexte
    )
    if localisation is None:
        raise ErreurAtelier(
            "Fragment introuvable dans le texte courant (zone déjà modifiée ?) — "
            "réévaluez le paragraphe avant de recommencer."
        )
    debut, fin = localisation
    try:
        reconstruction.appliquer_modification(etat, paragraphe_id, debut, fin, texte)
    except reconstruction.ZoneDejaModifiee as erreur:
        raise ErreurAtelier(str(erreur)) from erreur


async def appliquer_alternative(
    analyse, etat: dict, paragraphe_id: str, fragment: str, texte: str,
    contexte: str = "", revision: int | None = None,
) -> None:
    """Applique l'alternative choisie par l'auteur (clic droit sur sélection).
    FA6 : `revision` (optionnel) — CAS, 409 si l'état a changé ailleurs."""
    verifier_revision(etat, revision)
    await _appliquer_patch(etat, paragraphe_id, fragment, texte, contexte)
    await sauver_etat(analyse["id"], etat)


def _prochain_numero_reevaluation(etat: dict) -> int:
    """FA2 — identité documentaire : le compteur des ids de réévaluation est
    CONTINU à l'échelle du document (jamais remis à zéro par appel). Inspecte
    tous les ids existants (`c-XXXX` comme `c-rXXXX`) et retourne le prochain
    numéro disponible — deux réévaluations de paragraphes distincts ne peuvent
    plus produire le même id (collision constatée à l'audit post-F3)."""
    numero = 0
    for entree in etat["corrections"]:
        correspondance = re.fullmatch(r"c-(?:r)?(\d+)", entree["correction"].id)
        if correspondance:
            numero = max(numero, int(correspondance.group(1)))
    return numero


async def _reevaluer_corrections(analyse, etat, paragraphe_id: str) -> list[Correction]:
    """Relance les phases actives de l'analyse sur le SEUL paragraphe modifié
    (texte courant). Liste vide valide (jamais une panne).

    FA2 : les phases s'exécutent EN PARALLÈLE (`asyncio.gather`, comme le
    pipeline d'analyse initial) — zéro appel LLM ajouté, réévaluation plus
    rapide ; l'ordre d'attribution des ids reste déterministe (ordre des
    phases)."""
    texte = reconstruction.texte_paragraphe(etat, paragraphe_id)
    paragraphe = Paragraphe(id=paragraphe_id, texte=texte)
    options = json.loads(analyse["options_json"] or "{}")
    actives = service_analyse.phases_actives(analyse["categorie"] or "chapitre", options)
    client = service_analyse._client_llm()
    phases: list[str] = []
    taches = []
    for phase in actives:
        modele = _MODELE_REEVALUATION[phase]()
        if not modele:
            continue
        messages = service_prompts.prompt_phase_correction(
            phase, service_prompts.CONSIGNES_PHASES[phase], [paragraphe], settings.variante
        )
        phases.append(phase)
        taches.append(client.completer(
            modele, messages,
            temperature=settings.temperature_correction,
            max_tokens=service_analyse.budget_sortie_tokens(len(texte)),
            schema_modele=ReponseCorrections,
            verifier_troncature=True,
        ))
    sorties = await asyncio.gather(*taches)
    nouvelles: list[Correction] = []
    compteur = _prochain_numero_reevaluation(etat)
    for phase, sortie in zip(phases, sorties):
        for correction in service_reconciliation.extraire_corrections(sortie, phase):
            compteur += 1
            renommee = correction.model_copy(
                update={"id": f"c-r{compteur:04d}", "paragraphe_id": paragraphe_id}
            )
            reconciliee = service_reconciliation.reconcilier(renommee, paragraphe)
            if reconciliee is not None:
                nouvelles.append(reconciliee)
    return nouvelles


async def reevaluer(analyse, etat: dict, paragraphe_id: str, revision: int | None = None) -> None:
    """Réévaluation manuelle des corrections d'un paragraphe (bouton « ↻ »).
    FA6 : `revision` (optionnel) — CAS, 409 si l'état a changé ailleurs."""
    verifier_revision(etat, revision)
    try:
        nouvelles = await _reevaluer_corrections(analyse, etat, paragraphe_id)
    except Exception as erreur:  # noqa: BLE001 — l'atelier ne doit jamais se bloquer
        raise ErreurAtelier(
            f"Réévaluation impossible (modèle indisponible ?) : {erreur}"
        ) from erreur
    reconstruction.remplacer_corrections_paragraphe(etat, paragraphe_id, nouvelles)
    await sauver_etat(analyse["id"], etat)


async def appliquer_embellissement(
    analyse, etat: dict, paragraphe_id: str, fragment: str, texte: str,
    contexte: str = "", revision: int | None = None,
) -> None:
    """Applique l'embellissement choisi, PUIS réévalue les corrections du
    paragraphe. Zéro surprise (J2.5) : travail sur une COPIE — si la
    réévaluation échoue, RIEN n'est appliqué (aucun état partiel) et l'état du
    contexte reste inchangé. FA6 : `revision` (optionnel) — CAS, 409 si
    l'état a changé ailleurs."""
    verifier_revision(etat, revision)
    copie = copy.deepcopy(etat)
    await _appliquer_patch(copie, paragraphe_id, fragment, texte, contexte)
    try:
        nouvelles = await _reevaluer_corrections(analyse, copie, paragraphe_id)
    except Exception as erreur:  # noqa: BLE001 — aucun état partiel
        raise ErreurAtelier(
            "Réévaluation impossible après embellissement : "
            f"{erreur} — le texte n'a pas été modifié, réessayez."
        ) from erreur
    reconstruction.remplacer_corrections_paragraphe(copie, paragraphe_id, nouvelles)
    await sauver_etat(analyse["id"], copie)
    # Synchronise l'état du contexte (déjà en mémoire) avec la copie validée.
    etat.clear()
    etat.update(copie)


async def editer_paragraphe(
    analyse, etat: dict, paragraphe_id: str, texte: str, revision: int | None = None
) -> None:
    """Édition DIRECTE sans IA temps réel (UX4, décision 38) : remplace le texte
    COURANT affiché du paragraphe par ce que l'auteur a saisi — un patch
    indépendant ancré sur la base (jamais de splice + remappage). Le paragraphe
    est marqué modifié ; ses corrections et patches antérieurs sont retirés
    (ils se rapportaient à un texte qui n'existe plus).
    FA6 : `revision` (optionnel) — CAS, 409 si l'état a changé ailleurs."""
    verifier_revision(etat, revision)
    if not texte:
        raise ErreurAtelier("Le texte édité est vide.")
    if not reconstruction.remplacer_texte_paragraphe(etat, paragraphe_id, texte):
        raise ErreurAtelier("Aucune modification détectée.")
    await sauver_etat(analyse["id"], etat)


# --- Suggestions à la demande (aucun état modifié) ----------------------------


async def suggerer_embellissement(
    fragment: str, paragraphe_texte: str, contexte: str = ""
) -> dict:
    """Propose une réécriture embellie du passage sélectionné (contexte courant
    pris en compte). Aucun état modifié : l'auteur voit puis applique/annule."""
    fragment = (fragment or "").strip()
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
            max_tokens=service_analyse.budget_sortie_tokens(len(paragraphe_texte)),
            schema_modele=ReponseEmbellissement,
            verifier_troncature=True,
        )
        reponse = ReponseEmbellissement.model_validate(
            json.loads(service_reconciliation.nettoyer_sortie_llm(sortie))
        )
        return {"texte": reponse.texte, "explication": reponse.explication}
    except Exception as erreur:  # noqa: BLE001 — message explicite, jamais de fantôme
        return {"erreur": f"Embellissement indisponible : {erreur}"}


async def suggerer_alternatives(fragment: str, paragraphe_texte: str) -> dict:
    """Propose 3 à 5 alternatives (synonymes, champ lexical) cohérentes avec le
    contexte du passage sélectionné (clic droit). Aucun état modifié."""
    fragment = (fragment or "").strip()
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
        sortie = await client.completer(
            settings.modele_style, messages, temperature=0.7,
            max_tokens=service_analyse.budget_sortie_tokens(len(paragraphe_texte)),
            schema_modele=ReponseAlternatives,
            verifier_troncature=True,
        )
        reponse = ReponseAlternatives.model_validate(
            json.loads(service_reconciliation.nettoyer_sortie_llm(sortie))
        )
        return {"alternatives": reponse.alternatives, "explication": reponse.explication}
    except Exception as erreur:  # noqa: BLE001 — message explicite, jamais de fantôme
        return {"erreur": f"Alternatives indisponibles : {erreur}"}


# --- Workflow de fin de chapitre (J2.5) ---------------------------------------


async def nouvelle_version(analyse) -> int:
    """Soumet une NOUVELLE analyse dont le texte source est exactement le texte
    courant (le texte affiché, avec les choix et modifications de l'auteur).
    Retourne l'identifiant de la nouvelle analyse (le job est lancé)."""
    etat = await charger_etat(analyse)
    paragraphes_courants, _ = reconstruction.projeter_paragraphes(etat)
    nouveau_texte = service_texte_riche.serialiser_document_riche(paragraphes_courants)
    # ATTENTION (piège J2.1) : db.executer retourne (lastrowid, rowcount) —
    # c'est bien lastrowid qu'il faut récupérer, sinon redirection vers /analyses/1.
    nouvel_id, _ = await db.executer(
        "INSERT INTO analyses (projet_id, texte_source, options_json) VALUES (?, ?, ?)",
        (analyse["projet_id"], nouveau_texte, analyse["options_json"]),
    )
    tache = asyncio.create_task(service_analyse.executer(nouvel_id))
    _TACHES.add(tache)
    tache.add_done_callback(_TACHES.discard)
    return nouvel_id


async def valider(analyse) -> dict:
    """Valide officiellement le chapitre : enregistre dans `chapitres` le TEXTE
    AFFICHÉ au moment du clic (qu'il soit corrigé ou non), avec son hash
    SHA-256, après un backup natif SQLite ; « dernier validé gagne » fait
    avancer la chaîne N+1. Réservé aux Chapitres. Retourne un résumé
    `{numero, titre, hash}`."""
    if analyse["statut"] != "terminee":
        raise ErreurAtelier("Analyse non terminée.")
    if analyse["categorie"] != "chapitre":
        raise ErreurAtelier(
            "Seul un Chapitre peut être validé officiellement. "
            "Pour un Passage ou un Extrait, soumettez un autre texte."
        )

    etat = await charger_etat(analyse)
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
    return {"numero": numero, "titre": titre_texte, "hash": empreinte}