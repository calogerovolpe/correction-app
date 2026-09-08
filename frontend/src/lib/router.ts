import { readable } from 'svelte/store';

/** Routeur minimal (jalon F0) : hash-based, zéro dépendance, local-first.
 *  Évoluera au fil des jalons F1→F4 (accueil, soumission, suivi, atelier). */

function extraireChemin(): string {
  const hash = window.location.hash.replace(/^#/, '');
  return hash === '' ? '/' : hash;
}

/** Route courante réactive (chemin sans le « # »). */
export const routeCourante = readable<string>(extraireChemin(), (set) => {
  const mettreAJour = () => set(extraireChemin());
  window.addEventListener('hashchange', mettreAJour);
  return () => window.removeEventListener('hashchange', mettreAJour);
});

/** Navigation interne par hash. */
export function naviguer(chemin: string): void {
  if (extraireChemin() === chemin) return;
  window.location.hash = chemin;
}