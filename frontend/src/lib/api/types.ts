/** Types des ressources de l'API JSON /api/v1/.
 *  Établis au jalon F0 pour le client fetch typé ; précisés au fil des jalons
 *  F1→F3 quand les endpoints seront définis. */

export type StatutChaine = 'vierge' | 'ok' | 'rupture';

export interface Projet {
  projet_id: string;
  titre: string;
  actif: boolean;
  chain_status: StatutChaine;
  current_chapter_num: number | null;
  last_chapter_title: string | null;
  created_at: string;
}

export type StatutAnalyse = 'en_attente' | 'en_cours' | 'terminee' | 'echec' | 'rejetee';

export interface AnalyseLigne {
  id: number;
  statut: StatutAnalyse;
  categorie: string | null;
  extrait: string;
  cree_a: string;
}

export interface ErreurApi {
  detail?: string;
  message?: string;
}