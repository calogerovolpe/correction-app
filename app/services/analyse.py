"""Orchestration des analyses — cahier des charges §4.4 et §7 (jalon J2).

Séquence (adaptation v6 §14.1) :
  normalisation -> validation du remplacement (refus zéro token)
  -> chaîne N+1 (catégorie définitive) -> fail-fast (ping des modèles actifs)
  -> phases 3-6 parallèles (Option B : aucune panne tolérée, aucun résultat partiel)
  -> validation/réconciliation -> déduplication Style prioritaire -> écritures.

J2 : aucune écriture narrative (codex/journaux/chapitres — jalon J3) ; seules les
métadonnées `analyses` et `corrections` sont persistées."""

import asyncio
import json
import logging
from datetime import datetime

from app import db
from app.config import settings
from app.llm.client import ClientLLM
from app.llm.prompts import CONSIGNES_PHASES, prompt_phase_correction
from app.models import PannePhase
from app.services import chaine, reconciliation, texte_riche
from app.services.normalisation import (
    decouper_paragraphes,
    detecter_categorie,
    extraire_titre_chapitre,
    normaliser,
    verifier_taille,
)

JOURNAL = logging.getLogger("correction.analyse")

ORDRE_PHASES = ["forme", "style", "technique", "embellissement"]

GABARIT_FAIL_FAST = (
    "⛔ Exécution interrompue — la phase {nom} ne répond pas ({cause}).\n"
    "Aucune donnée narrative n'a été écrite. Vérifiez la configuration "
    "des modèles et renvoyez votre texte."
)
GABARIT_OPTION_B = (
    "⛔ Exécution interrompue — la phase {nom} a échoué en cours d'analyse ({cause}).\n"
    "Aucun document n'a été émis et aucune donnée narrative n'a été écrite.\n"
    "Vous pouvez renvoyer votre texte."
)

_MODELES = {
    "forme": lambda: settings.modele_forme,
    "style": lambda: settings.modele_style,
    "technique": lambda: settings.modele_technique,
    "embellissement": lambda: settings.modele_embellissement,
}


def phases_actives(categorie: str, choix: dict) -> list[str]:
    """Pré-sélection par défaut selon la matrice (v6 §5.4), DÉROGEABLE (décision de
    l'auteur, jalon J2) : l'interface pré-coche les phases selon la catégorie et
    l'utilisateur les coche/décoche librement — un Chapitre peut ainsi être corrigé
    pour la seule Forme, ou le seul Embellissement.

    `choix[phase]` : None = pré-sélection matrice ; True/False = choix explicite."""
    defauts = {
        "forme": True,
        "style": categorie == "chapitre",
        "technique": categorie == "chapitre",
        "embellissement": categorie in ("passage", "extrait"),
    }
    return [
        phase for phase in ORDRE_PHASES
        if (choix[phase] if choix.get(phase) is not None else defauts[phase])
    ]


def _client_llm() -> ClientLLM:
    """Fabrique injectable — les tests la remplacent par MockLLM."""
    return ClientLLM()


async def _maj(identifiant: int, **champs) -> None:
    if not champs:
        return
    assignations = ", ".join(f"{cle} = ?" for cle in champs)
    await db.executer(
        f"UPDATE analyses SET {assignations} WHERE id = ?",
        (*champs.values(), identifiant),
    )


def _maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


async def executer(identifiant: int) -> None:
    """Point d'entrée du job (cahier §4.4) — ne lève jamais : statut garanti final."""
    try:
        await _executer_interne(identifiant)
    except Exception as erreur:  # noqa: BLE001 — capture globale (v6 §14.2)
        JOURNAL.exception("Exception non interceptée dans l'analyse %s", identifiant)
        await _maj(identifiant, statut="echec", erreur=f"Exception inattendue : {erreur}",
                   fini_a=_maintenant())

async def _executer_interne(identifiant: int) -> None:
    lignes = await db.interroger("SELECT * FROM analyses WHERE id = ?", (identifiant,))
    if not lignes or lignes[0]["statut"] != "en_attente":
        return  # idempotence : ne jamais relancer un job terminé
    analyse = lignes[0]
    projets = await db.interroger("SELECT * FROM projets WHERE projet_id = ?",
                                  (analyse["projet_id"],))
    projet = projets[0]
    options = json.loads(analyse["options_json"] or "{}")

    await _maj(identifiant, statut="en_cours", etape="normalisation")
    source = analyse["texte_source"]

    # Support format riche (v2 JSON) ou texte brut (legacy)
    paragraphes_riches = texte_riche.parser_document_riche(source)
    if paragraphes_riches:
        paragraphes = texte_riche.convertir_en_paragraphes_simples(paragraphes_riches)
        texte = "\n".join(p.texte for p in paragraphes)
    else:
        texte = normaliser(source)
        paragraphes = decouper_paragraphes(texte)

    verifier_taille(texte, settings.max_caracteres)
    titre = extraire_titre_chapitre(texte)
    numero = titre[0] if titre else None
    categorie_naturelle = detecter_categorie(texte)

    # Validation du remplacement (v6 §14.1 étape 4) — refus zéro token
    remplacement_ok = False
    if options.get("remplacement"):
        existants = {
            ligne["numero"]
            for ligne in await db.interroger(
                "SELECT numero FROM chapitres WHERE projet_id = ?", (projet["projet_id"],)
            )
        }
        validation = chaine.valider_remplacement(projet, existants, None)
        if validation.decision == "refus_remplacement":
            await _maj(identifiant, statut="rejetee", decision=validation.decision,
                       message=validation.message, erreur=validation.message,
                       fini_a=_maintenant())
            return
        remplacement_ok = True

    # Chaîne N+1 (v6 §6.5) -> catégorie définitive
    await _maj(identifiant, etape="chaine")
    arbitrage = chaine.arbitrer(
        projet,
        numero,
        categorie_forcee=(
            options["categorie"] if options.get("categorie") in ("passage", "extrait") else None
        ),
        remplacement_demande=remplacement_ok,
        categorie_naturelle=categorie_naturelle,
    )
    if arbitrage.decision == "refus_remplacement":
        await _maj(identifiant, statut="rejetee", decision=arbitrage.decision,
                   message=arbitrage.message, erreur=arbitrage.message,
                   fini_a=_maintenant())
        return
    await _maj(identifiant, categorie=arbitrage.categorie, decision=arbitrage.decision,
               message=arbitrage.message)

    # Fail-fast (v6 §4) : zéro token d'analyse si un modèle indispensable manque
    await _maj(identifiant, etape="fail_fast")
    actives = phases_actives(arbitrage.categorie, options)
    modeles = {phase: _MODELES[phase]() for phase in actives}
    non_configures = [phase for phase, modele in modeles.items() if not modele]
    if non_configures:
        await _maj(identifiant, statut="rejetee",
                   erreur=f"Modèle non configuré pour la/les phase(s) : {', '.join(non_configures)}. "
                          "Renseignez les variables APP_MODELE_* dans .env.",
                   fini_a=_maintenant())
        return
    client = _client_llm()
    indisponibles = await client.verifier_disponibilite(modeles)
    if indisponibles:
        await _maj(identifiant, statut="rejetee",
                   erreur=GABARIT_FAIL_FAST.format(nom=", ".join(indisponibles),
                                                   cause="modèle indisponible"),
                   fini_a=_maintenant())
        return

    # Phases 3 à 6 parallèles (v6 §14.1 étape 8) — Option B en cas de panne
    await _maj(identifiant, etape="phases")
    temperature_embellissement = options.get("temperature_embellissement")
    try:
        resultats = await asyncio.gather(
            *(
                _executer_phase(client, phase, paragraphes, temperature_embellissement)
                for phase in actives
            )
        )
    except PannePhase as panne:
        await _maj(identifiant, statut="echec",
                   erreur=GABARIT_OPTION_B.format(nom=panne.phase, cause=panne.cause),
                   fini_a=_maintenant())
        return
    except Exception as erreur:  # noqa: BLE001
        await _maj(identifiant, statut="echec",
                   erreur=GABARIT_OPTION_B.format(nom="une phase", cause=str(erreur)),
                   fini_a=_maintenant())
        return

    toutes = [correction for resultat in resultats for correction in resultat]
    fusion = reconciliation.dedupliquer(toutes)

    # Écritures — métadonnées uniquement en J2 (narratif au jalon J3)
    await _maj(identifiant, etape="ecriture")
    await db.executer(
        "INSERT INTO corrections (analyse_id, data_json) VALUES (?, ?)",
        (identifiant, json.dumps([f.model_dump() for f in fusion], ensure_ascii=False)),
    )
    await _maj(identifiant, statut="terminee", etape=None, fini_a=_maintenant())


async def _executer_phase(client, phase: str, paragraphes, temperature_embellissement=None) -> list:
    """Une phase : prompt -> complétion -> extraction (PannePhase possible)
    -> réconciliation par correction (rejets individuels, jamais d'arrêt).

    Jauge de créativité (décision de l'auteur, jalon J2) : la température de
    l'Embellissement est choisie par l'utilisateur dans E3 (défaut : réglage global)."""
    messages = prompt_phase_correction(
        phase, CONSIGNES_PHASES[phase], paragraphes, settings.variante
    )
    if phase == "embellissement":
        temperature = (
            temperature_embellissement
            if temperature_embellissement is not None
            else settings.temperature_embellissement
        )
    else:
        temperature = settings.temperature_correction
    sortie = await client.completer(_MODELES[phase](), messages, temperature=temperature)
    corrections = reconciliation.extraire_corrections(sortie, phase)
    par_dict = {p.id: p for p in paragraphes}
    validees = []
    for correction in corrections:
        paragraphe = par_dict.get(correction.paragraphe_id)
        if paragraphe is None:
            JOURNAL.warning("Correction %s rejetée : paragraphe %s inconnu",
                            correction.id, correction.paragraphe_id)
            continue
        reconciliee = reconciliation.reconcilier(correction, paragraphe)
        if reconciliee is not None:
            validees.append(reconciliee)
    return validees
