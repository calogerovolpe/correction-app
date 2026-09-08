import { api } from './client';
import type { AnalyseSuivi, PreparerSoumission, SoumissionAnalyse } from './types';

/** Fonctions typées de l'API /api/v1 — Soumission E3 + suivi E4 (jalon F2).
 *  Contrairement au client générique (`api`), chaque fonction expose un
 *  contrat précis (chemin, corps, type de retour). */

/** État de préparation de E3 : projet actif, numéro N+1 attendu, dernières
 *  configurations mémorisées (J2.5) et garde-fou de taille. */
export function preparerSoumission(): Promise<PreparerSoumission> {
  return api.obtenir<PreparerSoumission>('/soumission');
}

/** Soumet un texte d'analyse (E3) et retourne le suivi initial du job. */
export function soumettreAnalyse(payload: SoumissionAnalyse): Promise<AnalyseSuivi> {
  return api.envoyer<AnalyseSuivi>('/analyses', payload);
}

/** Statut/suivi d'une analyse (E4) — lecture pure pour le polling. */
export function statutAnalyse(analyseId: number): Promise<AnalyseSuivi> {
  return api.obtenir<AnalyseSuivi>(`/analyses/${analyseId}`);
}