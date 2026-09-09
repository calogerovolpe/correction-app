import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mount, unmount } from 'svelte';
import type { Component } from 'svelte';

import Soumission from '../src/routes/Soumission.svelte';
import type { PreparerSoumission } from '../src/lib/api/types';

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

function preparation(surcharge: Partial<PreparerSoumission> = {}): PreparerSoumission {
  return {
    projet: {
      projet_id: 'P-AAAAAA',
      titre: 'Mon roman',
      actif: true,
      chain_status: 'ok',
      current_chapter_num: 3,
      last_chapter_title: 'La veille',
      created_at: '2026-09-09 12:00:00',
      derniere_analyse_id: 11,
    },
    numero_attendu: 4,
    prefil: { categorie: 'chapitre', phases: { forme: true, style: true, technique: true } },
    max_caracteres: 30000,
    ...surcharge,
  };
}

interface Filets {
  demandes: { methode: string; url: string; corps: string | null }[];
}

/** Remplace globalement `fetch` par une fausse API /api/v1 pilotable. */
function reparerFetch(
  prep: PreparerSoumission,
  filets?: Filets,
  statutSoumission: number = 201,
  detailSoumission: string | null = null,
): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: RequestInfo | URL, options: RequestInit = {}) => {
      const chemin = String(url);
      const methode = options.method ?? 'GET';
      filets?.demandes.push({ methode, url: chemin, corps: options.body ? String(options.body) : null });

      if (methode === 'GET' && chemin.endsWith('/api/v1/soumission')) {
        return reponseJson(prep);
      }
      if (methode === 'POST' && chemin.endsWith('/api/v1/analyses')) {
        if (statutSoumission === 400) {
          return reponseJson({ detail: detailSoumission }, 400);
        }
        return reponseJson(
          { id: 1, statut: 'en_attente', etape: null, erreur: null, categorie: null, cree_a: 'x', fini_a: null, resultat: null },
          201,
        );
      }
      return reponseJson({ detail: 'introuvable' }, 404);
    }),
  );
}

function casePhases(libelle: string): HTMLInputElement | undefined {
  const label = [...conteneur.querySelectorAll<HTMLLabelElement>('label')].find((l) =>
    l.textContent?.includes(libelle),
  );
  return label?.querySelector<HTMLInputElement>('input[type="checkbox"]') ?? undefined;
}

function radio(valeur: string): HTMLInputElement | undefined {
  return [...conteneur.querySelectorAll<HTMLInputElement>('input[type="radio"]')].find(
    (r) => r.value === valeur,
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
  window.location.hash = '';
});

describe('Soumission E3 (F2)', () => {
  it('pré-remplit le numéro N+1 et la matrice Chapitre', async () => {
    reparerFetch(preparation());
    rendre(Soumission);
    await attendre();
    await attendre();

    const numero = conteneur.querySelector<HTMLInputElement>('#numero-chapitre');
    expect(numero?.value).toBe('4');
    expect(conteneur.textContent).toContain('(attendu par la suite : 4)');
    expect(casePhases('Technique')?.checked).toBe(true);
    expect(casePhases('Forme')?.checked).toBe(true);
    expect(conteneur.textContent).toContain('30000');
  });

  it('réinitialise la matrice lors d\u2019un changement de catégorie', async () => {
    reparerFetch(preparation());
    rendre(Soumission);
    await attendre();
    await attendre();

    radio('extrait')!.click();
    await attendre();
    await attendre();

    expect(casePhases('Technique')?.checked).toBe(false);
    expect(casePhases('Forme')?.checked).toBe(true);
    expect(casePhases('Style')?.checked).toBe(true);
    // Options du Chapitre (numéro + codex) masquées pour un Extrait
    expect(conteneur.querySelector('#numero-chapitre')).toBeNull();
  });

  it('désactive le bouton tant que le texte est vide', async () => {
    reparerFetch(preparation());
    rendre(Soumission);
    await attendre();
    await attendre();

    const bouton = [...conteneur.querySelectorAll<HTMLButtonElement>('button')].find(
      (b) => b.textContent?.trim().includes("Lancer l'analyse"),
    );
    expect(bouton?.disabled).toBe(true);
  });
it('soumet le texte v2 puis navigue vers le suivi', async () => {
    const filets: Filets = { demandes: [] };
    reparerFetch(preparation(), filets);
    rendre(Soumission);
    await attendre();
    await attendre();

    const editeur = conteneur.querySelector<HTMLElement>('.editeur-word')!;
    editeur.innerHTML = '<p>Bonjour</p>';
    editeur.dispatchEvent(new Event('input', { bubbles: true }));
    await attendre();

    // Le compteur suit l'éditeur : le bouton s'active dès que du texte est saisi
    const bouton = [...conteneur.querySelectorAll<HTMLButtonElement>('button')].find(
      (b) => b.textContent?.trim().includes("Lancer l'analyse"),
    );
    expect(bouton?.disabled).toBe(false);

    const formulaire = conteneur.querySelector<HTMLFormElement>('form')!;
    formulaire.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await attendre();
    await attendre();

    const demande = filets.demandes.find(
      (d) => d.methode === 'POST' && d.url.endsWith('/api/v1/analyses'),
    );
    expect(demande).toBeDefined();
    const corps = JSON.parse(demande!.corps ?? '{}');
    expect(corps.texte).toBe(
      JSON.stringify([
        { id: 'p-1', runs: [{ texte: 'Bonjour', gras: false, italique: false, souligne: false }] },
      ]),
    );
    expect(corps.categorie).toBe('chapitre');
    expect(corps.numero_chapitre).toBe(4);
    expect(corps.phases).toEqual({ forme: true, style: true, technique: true });
    expect(window.location.hash).toBe('#/analyses/1');
  });

  it('affiche le refus explicite renvoyé par le serveur (400)', async () => {
    reparerFetch(
      preparation(),
      undefined,
      400,
      'Sélectionnez au moins un type de correction (Forme, Style ou Technique).',
    );
    rendre(Soumission);
    await attendre();
    await attendre();

    const editeur = conteneur.querySelector<HTMLElement>('.editeur-word')!;
    editeur.innerHTML = '<p>Bonjour</p>';
    editeur.dispatchEvent(new Event('input', { bubbles: true }));
    await attendre();

    // L'auteur décoche la matrice complète → le serveur refuse (400 explicite)
    const cases = [...conteneur.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')];
    for (const casePh of cases) {
      casePh.checked = false;
      casePh.dispatchEvent(new Event('change', { bubbles: true }));
    }
    await attendre();

    const formulaire = conteneur.querySelector<HTMLFormElement>('form')!;
    formulaire.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await attendre();
    await attendre();

    expect(conteneur.textContent).toContain('au moins un type de correction');
    expect(window.location.hash).not.toContain('/analyses/');
  });

  it('affiche un état vide quand aucun projet actif', async () => {
    reparerFetch(preparation({ projet: null, numero_attendu: 0 }));
    rendre(Soumission);
    await attendre();
    await attendre();

    expect(conteneur.textContent).toContain('Aucun projet actif');
    expect(conteneur.textContent).toContain("Revenir à l'accueil");
  });
});