import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mount, unmount } from 'svelte';
import type { Component } from 'svelte';

import Atelier from '../src/routes/Atelier.svelte';
import type { EtatAtelier } from '../src/lib/api/types';

let conteneur: HTMLElement;
let instances: unknown[] = [];

function rendre(
  composant: Component<any, any, any>,
  props: Record<string, unknown> = {},
): HTMLElement {
  const instance = mount(composant as never, { target: conteneur, props } as never);
  instances.push(instance);
  return conteneur;
}

const attendre = () => new Promise((resoudre) => setTimeout(resoudre, 0));

function reponseJson(corps: unknown, statut = 200): Response {
  return new Response(JSON.stringify(corps), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** État atelier minimal : une Forme (del/ins) + une Style (marquage). */
function etatAtelier(onglet: string): EtatAtelier {
  return {
    id: 7,
    statut: 'terminee',
    categorie: 'chapitre',
    onglet: onglet as EtatAtelier['onglet'],
    est_chapitre: true,
    a_embellissement: false,
    nb_corrections: 2,
    compteurs: { forme: 1, style: 1 },
    document: {
      paragraphes: [
        {
          id: 'p-1',
          edite: false,
          segments: [
            { type: 'texte', texte: 'Les cavaliers ', gras: false, italique: false, souligne: false, classes: '', groupe: null },
            { type: 'forme', groupe: 'g-0001', del: 'part', ins: 'partent', gras: false, italique: false, souligne: false, classes: '' },
            { type: 'texte', texte: " à l'aube vers la cité.", gras: false, italique: false, souligne: false, classes: 'mark-style', groupe: 'g-0002' },
          ],
        },
      ],
      nb_masques: 0,
      corrections_barre: [
        {
          id: 'c-0001', groupe: 'g-0001', phase: 'forme', type: 'accord_sujet_verbe',
          paragraphe_id: 'p-1', debut: 14, fin: 18, original: 'part', correction: 'partent',
          explication: 'Le sujet pluriel commande l’accord.', regle: 'Accord sujet-verbe',
          titre: 'Forme — accord sujet verbe', etat: 'active', motif: null, decision: 'corrige',
        },
        {
          id: 'c-0002', groupe: 'g-0002', phase: 'style', type: 'repetition',
          paragraphe_id: 'p-1', debut: 19, fin: 23, original: 'cité', correction: 'cité',
          explication: 'Répétition rapprochée.', regle: '', titre: 'Style — repetition',
          etat: 'active', motif: null,
        },
      ],
    },
  };
}

/** Remplace `fetch` : la fabrique reçoit l'URL et retourne la réponse. */
function reparerFetch(fabrique: (url: string) => Response): { appels: () => string[] } {
  const appels: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: RequestInfo | URL) => {
      const urlComplet = String(url);
      appels.push(urlComplet);
      return fabrique(urlComplet);
    }),
  );
  return { appels: () => appels };
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
  vi.unstubAllGlobals();
});

describe('Atelier E5 (F3)', () => {
  it('charge le document annoté et affiche les couches de correction', async () => {
    reparerFetch(() => reponseJson(etatAtelier('tout')));
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    expect(conteneur.textContent).toContain('Atelier — analyse #7');
    expect(conteneur.textContent).toContain('2 correction(s) active(s)');
    // Couches : correction Forme visible (del + ins) et marquage Style
    expect(conteneur.textContent).toContain('part');
    expect(conteneur.textContent).toContain('partent');
    // Les classes de couche sont portées par le DOM (pas le texte visible)
    expect(conteneur.querySelector('.del')).toBeTruthy();
    expect(conteneur.querySelector('.ins--forme')).toBeTruthy();
    expect(conteneur.querySelector('.mark-style')).toBeTruthy();
    // Onglets + compteurs
    expect(conteneur.textContent).toContain('Tout');
    expect(conteneur.textContent).toContain('Forme');
    expect(conteneur.textContent).toContain('Style');
    // Barre latérale
    expect(conteneur.textContent).toContain('Le sujet pluriel commande l’accord.');
  });

  it('change d’onglet via la projection par phase', async () => {
    const fetch = reparerFetch((url) => {
      const onglet = url.includes('onglet=forme') ? 'forme' : 'tout';
      return reponseJson(etatAtelier(onglet));
    });
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    const boutonForme = Array.from(conteneur.querySelectorAll('button')).find(
      (b) => b.textContent?.includes('Forme'),
    );
    expect(boutonForme).toBeTruthy();
    boutonForme?.click();
    await attendre();
    await attendre();

    expect(fetch.appels().some((u) => u.includes('onglet=forme'))).toBe(true);
  });

  it('affiche une erreur explicite quand l’atelier est introuvable', async () => {
    reparerFetch(() => reponseJson({ detail: 'Analyse introuvable.' }, 404));
    rendre(Atelier, { analyseId: 9999 });
    await attendre();
    await attendre();

    expect(conteneur.textContent).toContain('Analyse introuvable.');
  });
});