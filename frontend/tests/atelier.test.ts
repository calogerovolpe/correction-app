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
    // FA3 — plus d'impasse : le bloc d'échec de chargement propose Réessayer
    // et un retour à l'accueil (fin de l'attente infinie « Chargement… »).
    expect(conteneur.textContent).toContain("Réessayer de charger l'atelier");
    expect(conteneur.textContent).toContain("Revenir à l'accueil");
  });

  it('le bouton Réessayer relance le chargement après un échec (FA3)', async () => {
    let enPanne = true;
    const fetch = reparerFetch(() =>
      enPanne
        ? reponseJson({ detail: 'Erreur serveur (500).' }, 500)
        : reponseJson(etatAtelier('tout')),
    );
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    expect(conteneur.textContent).toContain('Erreur serveur (500).');
    const nbAppelsEnPanne = fetch.appels().length;

    enPanne = false;
    const boutonReessayer = Array.from(conteneur.querySelectorAll('button')).find(
      (b) => b.textContent?.includes('Réessayer'),
    );
    expect(boutonReessayer).toBeTruthy();
    boutonReessayer?.click();
    await attendre();
    await attendre();

    expect(fetch.appels().length).toBeGreaterThan(nbAppelsEnPanne);
    // l'atelier s'affiche enfin : couches, onglets, barre latérale
    expect(conteneur.textContent).toContain('2 correction(s) active(s)');
    expect(conteneur.querySelector('.ins--forme')).toBeTruthy();
  });

  it('rend les segments multi-marqués sans doublon de clé Svelte (FA4)', async () => {
    // Régression : depuis la segmentation atomique FA3, UNE même marque (ex.
    // `g-0004`) peut couvrir PLUSIEURS segments consécutifs, et des segments
    // sans groupe peuvent porter des textes identiques. L'ancienne clé
    // `f-${groupe}` / `t-${groupe ?? texte}` produisait des doublons ->
    // `each_key_duplicate` (crash runtime, atelier figé sur « Chargement… »).
    const etat = etatAtelier('tout');
    etat.document.paragraphes[0].segments = [
      { type: 'texte', texte: 'Lui, il voulait ', gras: false, italique: true, souligne: false, classes: '', groupe: null },
      // deux segments DISTINCTS partageant le MÊME groupe de marque
      { type: 'texte', texte: 'la voir', gras: false, italique: false, souligne: false, classes: 'mark-style', groupe: 'g-0004' },
      { type: 'texte', texte: '. Le sable se hissait', gras: false, italique: false, souligne: false, classes: 'mark-style', groupe: 'g-0004' },
      // texte neutre IDENTIQUE à un segment précédent (groupe null)
      { type: 'texte', texte: 'Lui, il voulait ', gras: false, italique: true, souligne: false, classes: '', groupe: null },
    ];

    const erreursConsole: unknown[] = [];
    const capturer = (e: ErrorEvent) => erreursConsole.push(e.error ?? e.message);
    window.addEventListener('error', capturer);

    reparerFetch(() => reponseJson(etat));
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();
    window.removeEventListener('error', capturer);

    // Aucune exception runtime : le document s'affiche entièrement
    expect(erreursConsole).toEqual([]);
    expect(conteneur.textContent).toContain('. Le sable se hissait');
    expect(conteneur.querySelector('.mark-style')).toBeTruthy();
  });

  it('rend le formatage Word du manuscrit (gras, italique, souligné) — FA4', async () => {
    // Les attributs `gras` / `italique` / `souligne` transmis par le rendu
    // backend (rendu.py, découpe atomique FA3) doivent devenir VISUELS dans le
    // DOM annoté : balisage sémantique <strong> / <em> / <u> emboîté.
    const etat = etatAtelier('tout');
    etat.document.paragraphes[0].segments = [
      { type: 'texte', texte: 'Le héros ', gras: true, italique: false, souligne: false, classes: '', groupe: null },
      { type: 'texte', texte: 'frémit ', gras: false, italique: true, souligne: false, classes: '', groupe: null },
      { type: 'texte', texte: 'et se ', gras: false, italique: false, souligne: true, classes: '', groupe: null },
      { type: 'texte', texte: 'releva.', gras: true, italique: true, souligne: true, classes: '', groupe: null },
      { type: 'forme', groupe: 'g-0001', del: 'part', ins: 'partent', gras: true, italique: false, souligne: false, classes: '' },
    ];

    reparerFetch(() => reponseJson(etat));
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    const doc = conteneur.querySelector('#document-annote');
    expect(doc?.querySelector('strong')?.textContent).toContain('Le héros');
    expect(doc?.querySelector('em')?.textContent).toContain('frémit');
    expect(doc?.querySelector('u')?.textContent).toBe('et se ');
    // Combinaison emboîtée : gras + italique + souligné = strong > em > u
    expect(doc?.querySelector('strong em u')?.textContent).toBe('releva.');
    // Les segments Forme héritent aussi du formatage (del ET ins)
    const insForme = conteneur.querySelector('button.ins--forme');
    expect(insForme).toBeTruthy();
    expect(insForme?.querySelector('strong')?.textContent).toBe('partent');
    // Les couches colorées conservent leurs classes (aucun reset ne les retire)
    expect(insForme?.classList.contains('ins--forme')).toBe(true);
  });

  it('conserve l’onglet actif après un choix Forme (pas de saut vers « tout ») — FA4', async () => {
    // L'auteur consulte l'onglet « Forme » ; appliquer une correction Forme ne
    // doit PAS ramener l'atelier sur l'onglet « Tout » : le POST transmet
    // `onglet=forme` et la réponse re-projette CET onglet.
    const fetch = reparerFetch(() => reponseJson(etatAtelier('forme')));
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    const marque = conteneur.querySelector(
      '[data-groupe="g-0001"]',
    ) as HTMLElement;
    expect(marque).toBeTruthy();
    marque.dispatchEvent(
      new MouseEvent('contextmenu', { bubbles: true, cancelable: true }),
    );
    await attendre();

    const boutonAppliquer = Array.from(conteneur.querySelectorAll('button')).find(
      (b) => b.textContent?.includes('Appliquer la correction'),
    );
    expect(boutonAppliquer).toBeTruthy();
    boutonAppliquer?.click();
    await attendre();
    await attendre();

    // Le POST a bien transmis l'onglet courant
    const appelPost = fetch.appels().find((u) => u.includes('choix-forme'));
    expect(appelPost).toBeTruthy();
    expect(appelPost).toContain('onglet=forme');
    // L'onglet « Forme » reste actif (aria-selected) — pas de saut vers « Tout »
    const ongletsActifs = Array.from(
      conteneur.querySelectorAll('[aria-selected="true"]'),
    );
    expect(ongletsActifs.length).toBeGreaterThan(0);
    expect(
      ongletsActifs.every((o) => o.textContent?.includes('Forme')),
    ).toBe(true);
    // La barre latérale reste réconciliée : une ligne active est surlignée
    expect(conteneur.querySelector('.barre-ligne--active')).toBeTruthy();
  });

  it('réconcilie la correction active après une mutation (id régénéré) — FA4', async () => {
    // Une réévaluation peut régénérer l'id de la correction : l'ancienne
    // référence de la barre latérale n'existe plus — la réconciliation doit
    // retomber proprement sur la première correction active.
    const etatApres = etatAtelier('tout');
    etatApres.document.corrections_barre[0].id = 'c-r0002';
    reparerFetch((url) =>
      reponseJson(url.includes('choix-forme') ? etatApres : etatAtelier('tout')),
    );
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    const marque = conteneur.querySelector(
      '[data-groupe="g-0001"]',
    ) as HTMLElement;
    marque.dispatchEvent(
      new MouseEvent('contextmenu', { bubbles: true, cancelable: true }),
    );
    await attendre();
    const boutonAppliquer = Array.from(conteneur.querySelectorAll('button')).find(
      (b) => b.textContent?.includes('Appliquer la correction'),
    );
    boutonAppliquer?.click();
    await attendre();
    await attendre();

    // Aucun détail fantôme : la ligne active pointe bien vers une correction
    // EXISTANTE de la nouvelle barre latérale (c-r0002)
    const ligneActive = conteneur.querySelector('.barre-ligne--active');
    expect(ligneActive).toBeTruthy();
    expect(ligneActive?.textContent).toContain('Forme');
  });

  it('bascule « masquer les paragraphes sans correction » — FA4', async () => {
    const etat = etatAtelier('tout');
    etat.document.paragraphes.push({
      id: 'p-2',
      edite: false,
      segments: [
        {
          type: 'texte',
          texte: 'Paragraphe sans aucune correction.',
          gras: false,
          italique: false,
          souligne: false,
          classes: '',
          groupe: null,
        },
      ],
    });
    etat.document.nb_masques = 1;
    reparerFetch(() => reponseJson(etat));
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    // Par défaut : TOUT le texte est affiché (décision 35)
    expect(conteneur.textContent).toContain('Paragraphe sans aucune correction.');

    const caseMasquer = conteneur.querySelector(
      '.toggle-masquer input',
    ) as HTMLInputElement;
    expect(caseMasquer).toBeTruthy();
    caseMasquer.checked = true;
    caseMasquer.dispatchEvent(new Event('change', { bubbles: true }));
    await attendre();

    expect(conteneur.textContent).not.toContain(
      'Paragraphe sans aucune correction.',
    );
    // Les paragraphes corrigés restent affichés
    expect(conteneur.textContent).toContain('Les cavaliers');

    caseMasquer.checked = false;
    caseMasquer.dispatchEvent(new Event('change', { bubbles: true }));
    await attendre();
    expect(conteneur.textContent).toContain('Paragraphe sans aucune correction.');
  });
});