import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { mount, unmount } from 'svelte';
import type { Component } from 'svelte';

import ConteneurToasts from '../src/lib/composants/ConteneurToasts.svelte';
import {
  afficherToast,
  fermerToast,
  toastErreur,
  toastInfo,
  toastSucces,
  toasts,
  viderToasts,
} from '../src/lib/toasts';

let conteneur: HTMLElement;
let instances: unknown[] = [];

function rendre(composant: Component, props: Record<string, unknown> = {}): HTMLElement {
  const instance = mount(composant as never, { target: conteneur, props } as never);
  instances.push(instance);
  return conteneur;
}

const attendre = () => new Promise((resoudre) => setTimeout(resoudre, 0));

beforeEach(() => {
  conteneur = document.createElement('div');
  document.body.appendChild(conteneur);
  instances = [];
  viderToasts();
});

afterEach(() => {
  vi.useRealTimers();
  for (const instance of instances) {
    unmount(instance as never);
  }
  instances = [];
  conteneur.remove();
  viderToasts();
});

describe('Store de toasts (F4)', () => {
  it('empile les toasts avec un identifiant unique', () => {
    const premier = afficherToast('succes', 'Premier');
    const second = afficherToast('erreur', 'Second');
    expect(premier).not.toBe(second);
    const file = get(toasts);
    expect(file.map((t) => t.message)).toEqual(['Premier', 'Second']);
    expect(file[0].type).toBe('succes');
    expect(file[1].type).toBe('erreur');
  });

  it('applique les durées par défaut (succès 5 s, erreur 8 s)', () => {
    const [succes, erreur] = [
      afficherToast('succes', 'Bravo'),
      afficherToast('erreur', 'Oups'),
    ];
    const file = get(toasts);
    expect(file.find((t) => t.id === succes)?.duree).toBe(5000);
    expect(file.find((t) => t.id === erreur)?.duree).toBe(8000);
  });

  it("ferme un toast manuellement (bouton ou appel d'API)", () => {
    const id = afficherToast('info', 'À noter');
    fermerToast(id);
    expect(get(toasts)).toHaveLength(0);
  });

  it('auto-ferme un toast après sa durée (minuterie)', () => {
    vi.useFakeTimers();
    toastSucces('Enregistré !');
    expect(get(toasts)).toHaveLength(1);
    vi.advanceTimersByTime(4999);
    expect(get(toasts)).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(get(toasts)).toHaveLength(0);
  });

  it('n\u2019auto-ferme PAS un toast à durée nulle (fermeture manuelle seule)', () => {
    vi.useFakeTimers();
    afficherToast('erreur', 'Bloquant', 0);
    vi.advanceTimersByTime(60_000);
    expect(get(toasts)).toHaveLength(1);
  });

  it('expose des raccourcis typés succès / info / erreur', () => {
    toastSucces('a');
    toastInfo('b');
    toastErreur('c');
    expect(get(toasts).map((t) => t.type)).toEqual(['succes', 'info', 'erreur']);
  });
});

describe('ConteneurToasts accessible (F4)', () => {
  it('annonce les succès avec role="status" + aria-live="polite"', async () => {
    rendre(ConteneurToasts);
    toastSucces('Paragraphe mis à jour.');
    await attendre();
    const zone = conteneur.querySelector('[role="status"]');
    expect(zone).toBeTruthy();
    expect(zone?.getAttribute('aria-live')).toBe('polite');
    expect(zone?.textContent).toContain('Paragraphe mis à jour.');
  });

  it('annonce les erreurs bloquantes avec role="alert" + aria-live="assertive"', async () => {
    rendre(ConteneurToasts);
    toastErreur('La soumission a échoué.');
    await attendre();
    const zone = conteneur.querySelector('[role="alert"]');
    expect(zone).toBeTruthy();
    expect(zone?.getAttribute('aria-live')).toBe('assertive');
    expect(zone?.textContent).toContain('La soumission a échoué.');
  });

  it('offre un bouton de fermeture accessible qui referme le toast', async () => {
    rendre(ConteneurToasts);
    toastSucces('Projet créé.');
    await attendre();
    const bouton = conteneur.querySelector<HTMLButtonElement>('.toast__fermer');
    expect(bouton?.getAttribute('aria-label')).toBe('Fermer la notification');
    bouton?.click();
    await attendre();
    expect(get(toasts)).toHaveLength(0);
    expect(conteneur.querySelector('.toast')).toBeNull();
  });

  it('trie les toasts : succès/infos dans la zone polie, erreurs dans la zone assertive', async () => {
    rendre(ConteneurToasts);
    toastSucces('Succès.');
    toastInfo('Info.');
    toastErreur('Erreur.');
    await attendre();
    const polie = conteneur.querySelector('[role="status"]')?.textContent ?? '';
    const assertive = conteneur.querySelector('[role="alert"]')?.textContent ?? '';
    expect(polie).toContain('Succès.');
    expect(polie).toContain('Info.');
    expect(polie).not.toContain('Erreur.');
    expect(assertive).toContain('Erreur.');
  });
});
