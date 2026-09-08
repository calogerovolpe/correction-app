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

export type CategorieAnalyse = 'chapitre' | 'passage' | 'extrait';

export interface PhasesSelection {
  forme: boolean;
  style: boolean;
  technique: boolean;
}

/** État final d'une analyse `terminee` (F2, suivi E4) : synthèse lecture seule
 *  comptée par phase. Le payload complet de l'atelier arrivera au jalon F3. */
export interface ResultatAnalyse {
  nb_corrections: number;
  par_phase: Record<string, number>;
}

/** Statut/suivi d'une analyse pour le polling (F2, E4) : statut explicite,
 *  étape courante, erreur (gabarits fail-fast / Option B) — jamais de statut
 *  fantôme côté client. */
export interface AnalyseSuivi {
  id: number;
  statut: StatutAnalyse;
  etape: string | null;
  erreur: string | null;
  categorie: string | null;
  cree_a: string | null;
  fini_a: string | null;
  resultat: ResultatAnalyse | null;
}

/** Corps du POST /api/v1/analyses (F2, E3) — équivalent JSON du formulaire E3. */
export interface SoumissionAnalyse {
  texte: string;
  categorie: CategorieAnalyse;
  numero_chapitre?: number | null;
  avec_codex?: boolean;
  phases?: PhasesSelection | null;
}

export interface PrefilSoumission {
  categorie: CategorieAnalyse;
  phases: PhasesSelection;
}

/** État de préparation de E3 (F2) : projet actif, numéro N+1 attendu, dernières
 *  configurations mémorisées (J2.5) et garde-fou de taille. */
export interface PreparerSoumission {
  projet: Projet | null;
  numero_attendu: number;
  prefil: PrefilSoumission;
  max_caracteres: number;
}

export interface ErreurApi {
  detail?: string;
  message?: string;
}