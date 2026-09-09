import { api } from './client';
import type {
  DecisionForme,
  DemandeSuggestion,
  EtatAtelier,
  ModificationSelection,
  OngletAtelier,
  ReponseNouvelleVersion,
  ReponseSuggestion,
  ReponseValidation,
} from './types';

/** Fonctions typées de l'API /api/v1 — Atelier E5 (jalon F3).
 *  Chaque fonction expose un contrat précis (chemin, corps, type de retour) ;
 *  la logique métier reste côté serveur (app/services/atelier.py). */

/** Document annoté de l'atelier : base immuable + annotations projetées selon
 *  l'onglet (tout = superposition, sinon une phase). Lecture pure. */
export function etatAtelier(
  analyseId: number,
  onglet?: OngletAtelier,
): Promise<EtatAtelier> {
  return api.obtenir<EtatAtelier>(`/analyses/${analyseId}/atelier`, {
    onglet: onglet ?? undefined,
  });
}

/** Accepte ('corrige') ou refuse ('original') une correction Forme (filtre).
 *  FA4 : `onglet` (optionnel) demande la projection de l'onglet courant — la
 *  réponse ne fait plus sauter l'atelier vers « tout ». */
export function choisirForme(
  analyseId: number,
  payload: DecisionForme,
  onglet?: OngletAtelier,
): Promise<EtatAtelier> {
  return api.envoyer<EtatAtelier>(
    `/analyses/${analyseId}/choix-forme`,
    payload,
    { onglet: onglet ?? undefined },
  );
}

/** Applique l'alternative choisie par l'auteur (clic droit sur sélection). */
export function appliquerAlternative(
  analyseId: number,
  payload: ModificationSelection,
  onglet?: OngletAtelier,
): Promise<EtatAtelier> {
  return api.envoyer<EtatAtelier>(
    `/analyses/${analyseId}/appliquer-alternative`,
    payload,
    { onglet: onglet ?? undefined },
  );
}

/** Édition directe sans IA temps réel : remplace le texte affiché du paragraphe
 *  (patch ancré base). « ↻ Re-corriger » relance le pipeline ensuite. */
export function editerParagraphe(
  analyseId: number,
  paragrapheId: string,
  texte: string,
  onglet?: OngletAtelier,
): Promise<EtatAtelier> {
  return api.envoyer<EtatAtelier>(
    `/analyses/${analyseId}/editer`,
    { paragraphe_id: paragrapheId, texte },
    { onglet: onglet ?? undefined },
  );
}

/** Réévaluation manuelle des corrections d'un paragraphe (bouton « ↻ »). */
export function reevaluerParagraphe(
  analyseId: number,
  paragrapheId: string,
  onglet?: OngletAtelier,
): Promise<EtatAtelier> {
  return api.envoyer<EtatAtelier>(
    `/analyses/${analyseId}/reevaluer`,
    { paragraphe_id: paragrapheId },
    { onglet: onglet ?? undefined },
  );
}

/** Applique l'embellissement choisi, PUIS réévalue les corrections du paragraphe
 *  (aucun état partiel si la réévaluation échoue). */
export function appliquerEmbellissement(
  analyseId: number,
  payload: ModificationSelection,
  onglet?: OngletAtelier,
): Promise<EtatAtelier> {
  return api.envoyer<EtatAtelier>(
    `/analyses/${analyseId}/appliquer-embellissement`,
    payload,
    { onglet: onglet ?? undefined },
  );
}

/** Soumet une nouvelle analyse dont le texte source est le texte affiché. */
export function nouvelleVersion(analyseId: number): Promise<ReponseNouvelleVersion> {
  return api.envoyer<ReponseNouvelleVersion>(
    `/analyses/${analyseId}/nouvelle-version`,
  );
}

/** Valide officiellement le chapitre (texte affiché + hash + avance la chaîne). */
export function validerAnalyse(analyseId: number): Promise<ReponseValidation> {
  return api.envoyer<ReponseValidation>(`/analyses/${analyseId}/valider`);
}

/** Propose une réécriture embellie du passage sélectionné (aucun état modifié). */
export function embellir(demande: DemandeSuggestion): Promise<ReponseSuggestion> {
  return api.envoyer<ReponseSuggestion>('/embellir', demande);
}

/** Propose des alternatives (synonymes, champ lexical) pour la sélection. */
export function alternatives(demande: DemandeSuggestion): Promise<ReponseSuggestion> {
  return api.envoyer<ReponseSuggestion>('/alternatives', demande);
}