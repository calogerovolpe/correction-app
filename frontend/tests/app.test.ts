import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { mount, unmount } from 'svelte';
import type { Component } from 'svelte';

import App from '../src/App.svelte';
import Accueil from '../src/routes/Accueil.svelte';

let conteneur: HTMLElement;
let instances: unknown[] = [];

// Les casts `as never` bornent les génériques stricts de mount/unmount :
// simple helper de test, sans conséquence sur l'application.
function rendre(composant: Component, props: Record<string, unknown> = {}): HTMLElement {
  const instance = mount(composant as never, { target: conteneur, props } as never);
  instances.push(instance);
  return conteneur;
}

beforeEach(() => {
  conteneur = document.createElement('div');
  document.body.appendChild(conteneur);
  instances = [];
});

afterEach(() => {
  for (const instance of instances) {
    unmount(instance as never);
  }
  instances = [];
  conteneur.remove();
});

describe('Coquille d’application (F0)', () => {
  it('affiche la marque et le pied de page', () => {
    rendre(App);
    expect(conteneur.textContent).toContain('Correction de manuscrit');
    expect(conteneur.textContent).toContain('vos textes restent sur votre machine');
  });

  it('affiche l’écran d’accueil par défaut', () => {
    rendre(App);
    expect(conteneur.textContent).toContain('Bienvenue dans votre atelier de correction');
  });
});

describe('Accueil (coquille F0)', () => {
  it('affiche un titre d’accueil accueillant', () => {
    rendre(Accueil);
    expect(conteneur.textContent).toContain('Bienvenue dans votre atelier de correction');
  });

  it('affiche l’état vide des manuscrits', () => {
    rendre(Accueil);
    expect(conteneur.textContent).toContain('Aucun manuscrit pour le moment');
  });
});