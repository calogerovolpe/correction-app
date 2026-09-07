"""Orchestration des analyses — cahier des charges §4.4 et §7 (jalons J2-J2.5).

Séquence (adaptation v6 §14.1) :
  normalisation -> chaîne déclarative (catégorie choisie par l'auteur)
  -> fail-fast (ping des modèles actifs) -> phases parallèles (Forme, Style,
  Technique) (Option B : aucune panne tolérée, aucun résultat partiel)
  -> validation/réconciliation -> déduplication -> écritures.

J2.5 : l'Embellissement n'est plus une phase d'analyse — il est demandé À LA
DEMANDE sur sélection (app/routes/atelier.py). Aucune écriture narrative ici
(chapitres/codex/journaux — jalon J3) ; seules les métadonnées `analyses` et
`corrections` sont persistées."""

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

ORDRE_PHASES = ["forme", "style", "technique"]

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
}


def phases_actives(categorie: str, choix: dict) -> list[str]:
    """Pré-sélection par défaut selon la catégorie, DÉROGABLE (décision de
    l'auteur, J2.1) : Chapitre = Forme + Style + Technique ; Passage/Extrait =
    Forme + Style. `choix[phase]` : None = pré-sélection ; True/False = choix
    explicite. L'Embellissement est demandé à la demande (J2.5), jamais ici."""
    defauts = {
        "forme": True,
        "style": True,
        "technique": categorie == "chapitre",
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

    # Catégorisation déclarative (J2.3) : l'utilisateur choisit la catégorie, Python respecte son choix.
    categorie_declaree = options.get("categorie", "chapitre")
    if categorie_declaree not in ("chapitre", "passage", "extrait"):
        categorie_declaree = "chapitre"

    numero_chapitre = options.get("numero_chapitre")
    if categorie_declaree == "chapitre" and numero_chapitre is not None:
        try:
            numero = float(numero_chapitre)
        except (ValueError, TypeError):
            numero = None
    else:
        numero = None

    await _maj(identifiant, categorie=categorie_declaree, decision=categorie_declaree, message=None)

    # Fail-fast (v6 §4) : zéro token d'analyse si un modèle indispensable manque
    await _maj(identifiant, etape="fail_fast")
    actives = phases_actives(categorie_declaree, options)
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

    # Phases parallèles (v6 §14.1 étape 8) — Option B en cas de panne
    await _maj(identifiant, etape="phases")
    try:
        resultats = await asyncio.gather(
            *(
                _executer_phase(client, phase, paragraphes)
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
    # IDs globaux uniques et déterministes (jalon A) : chaque phase émet ses
    # propres ids sans coordination — un doublon casserait les groupes g-XXXX
    # du rendu (barre latérale désynchronisée, choix Forme partagés).
    fusion = reconciliation.renumeroter(fusion)

    # Écritures — métadonnées uniquement en J2 (narratif au jalon J3)
    await _maj(identifiant, etape="ecriture")
    await db.executer(
        "INSERT INTO corrections (analyse_id, data_json) VALUES (?, ?)",
        (identifiant, json.dumps([f.model_dump() for f in fusion], ensure_ascii=False)),
    )
    await _maj(identifiant, statut="terminee", etape=None, fini_a=_maintenant())


async def _executer_phase(client, phase: str, paragraphes) -> list:
    """Une phase : prompt -> complétion -> extraction (PannePhase possible)
    -> réconciliation par correction (rejets individuels, jamais d'arrêt).

    Les phases de correction tournent toujours à température 0.0 ; la jauge
    de créativité ne concerne que l'Embellissement, désormais à la demande (J2.5)."""
    messages = prompt_phase_correction(
        phase, CONSIGNES_PHASES[phase], paragraphes, settings.variante
    )
    sortie = await client.completer(
        _MODELES[phase](), messages, temperature=settings.temperature_correction
    )
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
