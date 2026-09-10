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
  /** FA2 — bouton « Ouvrir » : id de la dernière analyse TERMINÉE du projet
   *  (l'atelier E5 n'est accessible que pour une analyse terminee) ;
   *  null → l'ouverture mène à la soumission. */
  derniere_analyse_id: number | null;
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

/** Corps du POST /api/v1/analyses (F2, E3) — équivalent JSON du formulaire E3.
 *  FA6 : `modele` = modèle texte Mistral choisi par l'auteur (catalogue) ;
 *  absent → configuration `.env` par phase (repli transparent). */
export interface SoumissionAnalyse {
  texte: string;
  categorie: CategorieAnalyse;
  numero_chapitre?: number | null;
  avec_codex?: boolean;
  phases?: PhasesSelection | null;
  modele?: string | null;
}

/** FA6 — entrée du catalogue des modèles texte Mistral (sélection de l'IA
 *  qui corrigera, affichée dans E3). */
export interface ModeleIa {
  id: string;
  libelle: string;
  badge: string | null;
  description: string;
}

export interface PrefilSoumission {
  categorie: CategorieAnalyse;
  phases: PhasesSelection;
}

/** État de préparation de E3 (F2) : projet actif, numéro N+1 attendu, dernières
 *  configurations mémorisées (J2.5) et garde-fou de taille. FA6 : catalogue
 *  des modèles texte + modèle par défaut + dernier choix valide mémorisé. */
export interface PreparerSoumission {
  projet: Projet | null;
  numero_attendu: number;
  prefil: PrefilSoumission;
  max_caracteres: number;
  modeles: ModeleIa[];
  modele_defaut: string;
  modele_memorise: string | null;
}

export interface ErreurApi {
  detail?: string;
  message?: string;
}

// --- F3 : Atelier E5 ----------------------------------------------------------
// Contrat JSON GET /api/v1/analyses/{id}/atelier : le document annoté (couches,
// onglets par phase, barre latérale) et les métadonnées nécessaires à E5.

export type OngletAtelier = 'tout' | 'forme' | 'style' | 'technique' | 'embellissement';

export interface SegmentTexte {
  type: 'texte';
  texte: string;
  gras: boolean;
  italique: boolean;
  souligne: boolean;
  classes: string;
  groupe: string | null;
}

export interface SegmentForme {
  type: 'forme';
  groupe: string;
  del: string;
  ins: string;
  gras: boolean;
  italique: boolean;
  souligne: boolean;
  classes: string;
}

export type SegmentAnnote = SegmentTexte | SegmentForme;

export interface ParagrapheAnnote {
  id: string;
  edite: boolean;
  segments: SegmentAnnote[];
}

export interface CorrectionBarre {
  id: string;
  groupe: string;
  phase: string;
  type: string;
  paragraphe_id: string;
  debut: number;
  fin: number;
  original: string;
  correction: string;
  explication: string;
  regle: string;
  titre: string;
  etat: string;
  motif: string | null;
  decision?: string | null;
}

export interface DocumentAnnote {
  paragraphes: ParagrapheAnnote[];
  nb_masques: number;
  corrections_barre: CorrectionBarre[];
}

export interface EtatAtelier {
  id: number;
  statut: string;
  categorie: string | null;
  onglet: OngletAtelier;
  est_chapitre: boolean;
  a_embellissement: boolean;
  nb_corrections: number;
  compteurs: Record<string, number>;
  document: DocumentAnnote;
  /** FA6 — compteur de cohérence transactionnelle : retransmis avec chaque
   *  mutation (conflit de révision → 409, jamais d'écrasement silencieux). */
  revision: number;
}

export interface DecisionForme {
  correction_id: string;
  decision: 'corrige' | 'original';
}

export interface ModificationSelection {
  paragraphe_id: string;
  fragment: string;
  texte: string;
  contexte?: string;
}

export interface DemandeSuggestion {
  fragment: string;
  paragraphe_texte: string;
  contexte?: string;
}

export interface ReponseSuggestion {
  texte?: string;
  explication?: string;
  alternatives?: string[];
  erreur?: string;
}

export interface ReponseNouvelleVersion {
  nouvel_id: number;
}

export interface ReponseValidation {
  ok: boolean;
  numero: number;
  titre: string;
  hash: string;
}