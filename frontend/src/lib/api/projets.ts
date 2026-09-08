import { api } from './client';
import type { AnalyseLigne, Projet } from './types';

/** Fonctions typées de l'API /api/v1 — Accueil & projets (jalon F1).
 *  Contrairement au client générique (`api`), chaque fonction expose un
 *  contrat précis (chemin, corps, type de retour). */

export interface ReponseProjets {
  projets: Projet[];
}

export interface ReponseAnalyses {
  analyses: AnalyseLigne[];
}

export function listerProjets(): Promise<ReponseProjets> {
  return api.obtenir<ReponseProjets>('/projets');
}

export function creerProjet(titre: string): Promise<Projet> {
  return api.envoyer<Projet>('/projets', { titre });
}

export function activerProjet(projetId: string): Promise<void> {
  return api.envoyer<void>(`/projets/${encodeURIComponent(projetId)}/activer`);
}

export function supprimerProjet(projetId: string): Promise<void> {
  return api.supprimer<void>(`/projets/${encodeURIComponent(projetId)}`);
}

export function analysesRecentes(): Promise<ReponseAnalyses> {
  return api.obtenir<ReponseAnalyses>('/analyses');
}