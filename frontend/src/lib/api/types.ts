/** Types des ressources de l'API JSON /api/v1/.
 *  Établis au jalon F0 pour le client fetch typé ; précisés au fil des jalons
 *  F1→F3 quand les endpoints seront définis. */

export interface Projet {
  projet_id: string;
  titre: string;
  actif: boolean;
  created_at: string;
}

export type StatutAnalyse = 'en_attente' | 'en_cours' | 'terminee' | 'echec' | 'rejetee';

export interface AnalyseLigne {
  id: number;
  statut: StatutAnalyse;
  categorie: string;
  extrait: string;
  cree_a: string;
}

export interface ErreurApi {
  detail?: string;
  message?: string;
}