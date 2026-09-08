import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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

const attendre = () => new Promise((resoudre) => setTimeout(resoudre, 0));

const reponseJson = (corps: unknown) =>
  new Response(JSON.stringify(corps), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

beforeEach(() => {
  conteneur = document.createElement('div');
  document.body.appendChild(conteneur);
  instances = [];
  // Depuis F1, l'accueil charge ses données via /api/v1 : on mime une base
  // vierge pour que les tests restent herméétiques (aucun réseau réel).
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: RequestInfo | URL) => {
      const chemin = String(url);
      if (chemin.includes('/api/v1/analyses')) return reponseJson({ analyses: [] });
      if (chemin.includes('/api/v1/projets')) return reponseJson({ projets: [] });
      return reponseJson({ detail: 'introuvable' });
    }),
  );
});

afterEach(() => {
  for (const instance of instances) {
    unmount(instance as never);
  }
  instances = [];
  conteneur.remove();
  vi.unstubAllGlobals();
});

describe("Coquille d'application (F0)", () => {
  it('affiche la marque et le pied de page', () => {
    rendre(App);
    expect(conteneur.textContent).toContain('Correction de manuscrit');
    expect(conteneur.textContent).toContain('vos textes restent sur votre machine');
  });

  it("affiche l'écran d'accueil par défaut", () => {
    rendre(App);
    expect(conteneur.textContent).toContain('Bienvenue dans votre atelier de correction');
  });
});

describe('Accueil (F1)', () => {
  it("affiche le titre d'accueil", () => {
    rendre(Accueil);
    expect(conteneur.textContent).toContain('Bienvenue dans votre atelier de correction');
  });

  it("affiche l'état vide après chargement", async () => {
    rendre(Accueil);
    await attendre();
    expect(conteneur.textContent).toContain('Aucun manuscrit pour le moment');
    expect(conteneur.textContent).toContain('Aucune analyse récente');
  });
});