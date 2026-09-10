/** frontend/src/lib/pedagogie.ts
 *  FA7 — Restitution pédagogique : découpage de la trame pédagogique des
 *  explications générées depuis le jalon FA5 (`app/llm/prompts.py ::
 *  TRAME_EXPLICATION`) en quatre temps — Cause → Règle → Correction → Effet.
 *  Fonction PURE (aucun DOM, testable isolément) : si l'explication ne suit
 *  pas la trame (analyses anciennes, format libre), le repli est un affichage
 *  brut — jamais d'affichage cassé. */

export type TempsTrame = 'cause' | 'regle' | 'correction' | 'effet';

export interface TrameExplication {
  cause: string;
  regle: string;
  correction: string;
  effet: string;
}

/** Motifs des intitulés explicites posés par TRAME_EXPLICATION (FA5) :
 *  « Cause : … Règle : … Correction : … Effet : … ». L'accent de « Règle »
 *  est tolérant (è/e) et le pluriel accepté — défense élémentaire contre les
 *  variations du LLM. */
const MOTIFS: { cle: TempsTrame; motif: RegExp }[] = [
  { cle: 'cause', motif: /\bcauses?\s*:/i },
  { cle: 'regle', motif: /\br[èe]gles?\s*:/i },
  { cle: 'correction', motif: /\bcorrections?\s*:/i },
  { cle: 'effet', motif: /\beffets?\s*:/i },
];

/** Découpe une explication selon la trame pédagogique en 4 temps.
 *  Retourne `null` si la trame n'est pas reconnaissable (moins de deux temps,
 *  intitulés hors ordre canonique) — l'appelant affiche alors l'explication
 *  brute. Chaque temps absent de l'explication est retourné vide (''). */
export function decouperTrame(explication: string): TrameExplication | null {
  const ordre: TempsTrame[] = ['cause', 'regle', 'correction', 'effet'];
  const marques: { cle: TempsTrame; debut: number; apres: number }[] = [];
  for (const { cle, motif } of MOTIFS) {
    const trouve = motif.exec(explication);
    if (trouve) {
      marques.push({ cle, debut: trouve.index, apres: trouve.index + trouve[0].length });
    }
  }
  // Moins de deux temps reconnaissables : pas une trame — repli brut.
  if (marques.length < 2) return null;
  marques.sort((a, b) => a.debut - b.debut);
  const indices = marques.map((m) => ordre.indexOf(m.cle));
  if (indices.some((i) => i === -1)) return null;
  // Les intitulés doivent suivre l'ordre canonique Cause → Règle → Correction → Effet.
  for (let i = 1; i < indices.length; i++) {
    if (indices[i] <= indices[i - 1]) return null;
  }
  const resultat: Record<TempsTrame, string> = {
    cause: '',
    regle: '',
    correction: '',
    effet: '',
  };
  marques.forEach((marque, i) => {
    const fin = i + 1 < marques.length ? marques[i + 1].debut : explication.length;
    resultat[marque.cle] = explication
      .slice(marque.apres, fin)
      .replace(/[\s.;,]+$/g, '')
      .trim();
  });
  return resultat;
}

/** Résumé rapide d'une explication : la première phrase (pour l'info-bulle). */
export function premierePhrase(explication: string): string {
  const phrase = explication.split(/(?<=[.!?])\s/)[0] ?? explication;
  return phrase.trim();
}