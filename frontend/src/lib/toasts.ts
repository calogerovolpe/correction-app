import { writable } from 'svelte/store';

/** Notifications toast (jalon F4) : conteneur unifié de messages fugitifs,
 *  accessibles aux lecteurs d'écran — succès/infos annoncés POLIMENT
 *  (`role="status"`, `aria-live="polite"`), erreurs bloquantes annoncées
 *  de façon ASSERTIVE (`role="alert"`, `aria-live="assertive"`).
 *  Auto-fermeture minutée paramétrable + bouton de fermeture manuelle.
 *  Le store est un `writable` svelte/store (convention du projet, cf.
 *  `router.ts`) : les toasts SURVIVENT à la navigation interne, puisque le
 *  conteneur est monté une seule fois dans `App.svelte`. */

export type TypeToast = 'succes' | 'info' | 'erreur';

export interface Toast {
  /** Identifiant unique et croissant (clé Svelte + fermeture ciblée). */
  id: number;
  type: TypeToast;
  message: string;
  /** Durée avant auto-fermeture, en ms ; 0 = jamais (fermeture manuelle). */
  duree: number;
}

/** Durées par défaut : confortables pour Camille (le temps de lire), les
 *  erreurs restent plus longtemps à l'écran que les succès. */
const DUREE_DEFAUT: Record<TypeToast, number> = {
  succes: 5000,
  info: 6000,
  erreur: 8000,
};

/** File actuelle des toasts (les plus récents en fin de liste). */
export const toasts = writable<Toast[]>([]);

let compteur = 0;
const minuteries = new Map<number, ReturnType<typeof setTimeout>>();

/** Affiche un toast et retourne son identifiant. */
export function afficherToast(
  type: TypeToast,
  message: string,
  duree?: number,
): number {
  compteur += 1;
  const id = compteur;
  const dureeFinale = duree ?? DUREE_DEFAUT[type];
  toasts.update((file) => [...file, { id, type, message, duree: dureeFinale }]);
  if (dureeFinale > 0) {
    minuteries.set(
      id,
      setTimeout(() => fermerToast(id), dureeFinale),
    );
  }
  return id;
}

/** Ferme un toast précis (bouton de fermeture ou auto-fermeture). */
export function fermerToast(id: number): void {
  const minuterie = minuteries.get(id);
  if (minuterie !== undefined) {
    clearTimeout(minuterie);
    minuteries.delete(id);
  }
  toasts.update((file) => file.filter((t) => t.id !== id));
}

/** Succès : annonce polie (`role="status"`, `aria-live="polite"`). */
export function toastSucces(message: string, duree?: number): number {
  return afficherToast('succes', message, duree);
}

/** Information neutre : annonce polie. */
export function toastInfo(message: string, duree?: number): number {
  return afficherToast('info', message, duree);
}

/** Erreur bloquante : annonce assertive (`role="alert"`). */
export function toastErreur(message: string, duree?: number): number {
  return afficherToast('erreur', message, duree);
}

/** Réinitialisation complète (tests uniquement — usage applicatif interdit). */
export function viderToasts(): void {
  for (const [id, minuterie] of minuteries) {
    clearTimeout(minuterie);
    minuteries.delete(id);
  }
  toasts.set([]);
}