import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mount, unmount } from 'svelte';
import type { Component } from 'svelte';

import Accueil from '../src/routes/Accueil.svelte';
import type { AnalyseLigne, Projet } from '../src/lib/api/types';

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

function reponseJson(corps: unknown, statut = 200): Response {
  return new Response(JSON.stringify(corps), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

function projet(surcharge: Partial<Projet> = {}): Projet {
  return {
    projet_id: 'P-AAAAAA',
    titre: 'Mon roman',
    actif: true,
    chain_status: 'vierge',
    current_chapter_num: null,
    last_chapter_title: null,
    created_at: '2026-09-09 12:00:00',
    ...surcharge,
  };
}

interface Filets {
  demandes: { methode: string; url: string; corps: string | null }[];
}

/** Remplace globalement `fetch` par une fausse API /api/v1 pilotable. */
function reparerFetch(projets: Projet[], analyses: AnalyseLigne[], filets?: Filets): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: RequestInfo | URL, options: RequestInit = {}) => {
      const chemin = String(url);
      const methode = options.method ?? 'GET';
      filets?.demandes.push({
        methode,
        url: chemin,
        corps: options.body ? String(options.body) : null,
      });

      if (methode === 'POST' && chemin.endsWith('/api/v1/projets')) {
        return reponseJson(
          { ...projet({ projet_id: 'P-ABABAB', titre: 'Nouveau roman', actif: false }) },
          201,
        );
      }
      if (methode === 'GET' && chemin.endsWith('/api/v1/projets')) {
        return reponseJson({ projets });
      }
      if (methode === 'POST' && chemin.includes('/activer')) {
        return new Response(null, { status: 204 });
      }
      if (methode === 'DELETE' && chemin.includes('/api/v1/projets/')) {
        return new Response(null, { status: 204 });
      }
      if (chemin.endsWith('/api/v1/analyses')) {
        return reponseJson({ analyses });
      }
      return reponseJson({ detail: 'introuvable' }, 404);
    }),
  );
}

function bouton(texte: string): HTMLButtonElement | undefined {
  return [...conteneur.querySelectorAll<HTMLButtonElement>('button')].find(
    (b) => !b.disabled && b.textContent?.trim().includes(texte),
  );
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

describe('Accueil & projets (F1)', () => {
  it('affiche les états vides quand aucun projet ni analyse', async () => {
    reparerFetch([], []);
    rendre(Accueil);
    await attendre();

    expect(conteneur.textContent).toContain('Bienvenue dans votre atelier de correction');
    expect(conteneur.textContent).toContain('Aucun manuscrit pour le moment');
    expect(conteneur.textContent).toContain('Aucune analyse récente');
  });

  it('liste les projets avec badge actif et états de chaîne', async () => {
    reparerFetch(
      [
        projet({ projet_id: 'P-AAABBB', titre: 'Premier roman', actif: true }),
        projet({
          projet_id: 'P-CCCDDD',
          titre: 'Second roman',
          actif: false,
          chain_status: 'ok',
          current_chapter_num: 2,
          last_chapter_title: 'Chapitre 2',
        }),
      ],
      [],
    );
    rendre(Accueil);
    await attendre();

    expect(conteneur.querySelectorAll('.projets__projet')).toHaveLength(2);
    expect(conteneur.textContent).toContain('Premier roman');
    expect(conteneur.textContent).toContain('Second roman');
    expect(conteneur.textContent).toContain('actif');
    expect(conteneur.textContent).toContain('chaîne cohérente');
    expect(conteneur.textContent).toContain('Chapitre 2');
  });

  it('crée un projet depuis le formulaire', async () => {
    const filets: Filets = { demandes: [] };
    reparerFetch([], [], filets);
    rendre(Accueil);
    await attendre();

    const champ = conteneur.querySelector<HTMLInputElement>('#titre-projet')!;
    champ.value = 'Nouveau roman';
    champ.dispatchEvent(new Event('input'));
    await attendre();

    const formulaire = conteneur.querySelector<HTMLFormElement>('form.creation')!;
    formulaire.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await attendre();
    await attendre();

    const creation = filets.demandes.find(
      (d) => d.methode === 'POST' && d.url.endsWith('/api/v1/projets'),
    );
    expect(creation).toBeDefined();
    expect(JSON.parse(creation!.corps ?? '{}')).toEqual({ titre: 'Nouveau roman' });
    // Après rechargement, le formulaire re-rendu est vide (titre remis à '').
    const champRelu = conteneur.querySelector<HTMLInputElement>('#titre-projet');
    expect(champRelu?.value ?? '').toBe('');
  });

  it('active un projet non actif', async () => {
    const filets: Filets = { demandes: [] };
    reparerFetch(
      [projet({ actif: true }), projet({ projet_id: 'P-CCCDDD', titre: 'Second', actif: false })],
      [],
      filets,
    );
    rendre(Accueil);
    await attendre();

    bouton('Activer')?.click();
    await attendre();
    await attendre();

    expect(
      filets.demandes.some((d) => d.methode === 'POST' && d.url.includes('/activer')),
    ).toBe(true);
  });

  it('supprime un projet après confirmation', async () => {
    const filets: Filets = { demandes: [] };
    reparerFetch(
      [projet({ actif: true }), projet({ projet_id: 'P-CCCDDD', titre: 'Second', actif: false })],
      [],
      filets,
    );
    rendre(Accueil);
    await attendre();

    bouton('Supprimer')?.click();
    await attendre();
    expect(conteneur.textContent).toContain('Supprimer définitivement');

    bouton('Supprimer définitivement')?.click();
    await attendre();
    await attendre();

    expect(
      filets.demandes.some(
        (d) => d.methode === 'DELETE' && d.url.includes('/api/v1/projets/P-CCCDDD'),
      ),
    ).toBe(true);
  });

  it('désactive la suppression du projet actif', async () => {
    reparerFetch([projet({ actif: true })], []);
    rendre(Accueil);
    await attendre();

    const boutonSupprimer = [...conteneur.querySelectorAll<HTMLButtonElement>('button')].find(
      (b) => b.textContent?.trim() === 'Supprimer',
    );
    expect(boutonSupprimer?.disabled).toBe(true);
  });

  it('affiche les analyses récentes cliquables', async () => {
    reparerFetch([projet({ actif: true })], [
      { id: 7, statut: 'terminee', categorie: 'chapitre', extrait: 'Il faisait beau', cree_a: '2026-09-09 10:00:00' },
    ]);
    rendre(Accueil);
    await attendre();

    expect(conteneur.textContent).toContain('terminée');
    const lien = conteneur.querySelector<HTMLAnchorElement>('.analyses__lien');
    expect(lien?.getAttribute('href')).toBe('/analyses/7');
  });
});