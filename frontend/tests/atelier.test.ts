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
    revision: 3,
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
let urlsAppellees: string[] = [];

function reparerFetch(fabrique: (url: string) => Response): { appels: () => string[] } {
  urlsAppellees = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: RequestInfo | URL) => {
      const urlComplet = String(url);
      urlsAppellees.push(urlComplet);
      return fabrique(urlComplet);
    }),
  );
  return { appels: () => urlsAppellees };
}

function appelsCaptures(): string[] {
  return urlsAppellees;
}

beforeEach(() => {
  conteneur = document.createElement('div');
  document.body.appendChild(conteneur);
  instances = [];
  // FA7 — jsdom n'implémente pas scrollIntoView : stub partagé pour affirmer
  // les appels de la liaison bidirectionnelle texte ↔ barre latérale.
  Element.prototype.scrollIntoView = vi.fn();
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

  it('transmet la révision courante avec chaque mutation — FA6', async () => {
    reparerFetch((url) => {
      if (url.includes('choix-forme')) {
        // La mutation est acceptée : la révision renvoyée avance.
        const etat = etatAtelier('tout');
        etat.revision = 4;
        return reponseJson(etat);
      }
      return reponseJson(etatAtelier('tout'));
    });
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    const marque = conteneur.querySelector('[data-groupe="g-0001"]') as HTMLElement;
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

    const appelPost = appelsCaptures().find((a) => a.includes('choix-forme'));
    expect(appelPost).toBeTruthy();
    // FA6 : la révision courante (3) est transmise en query de la mutation
    expect(appelPost).toContain('revision=3');
  });

  it('resynchronise l\'atelier après un conflit de révision (409) — FA6', async () => {
    let premierAppelPost = true;
    reparerFetch((url) => {
      if (url.includes('choix-forme')) {
        if (premierAppelPost) {
          premierAppelPost = false;
          return reponseJson({ detail: 'L\'atelier a été modifié dans un autre onglet ou une autre session (révision périmée). Rechargez la page pour récupérer l\'état à jour avant de réessayer.' }, 409);
        }
      }
      return reponseJson(etatAtelier('tout'));
    });
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    const marque = conteneur.querySelector('[data-groupe="g-0001"]') as HTMLElement;
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
    await attendre();

    // Le message de conflit est affiché ET l'atelier est automatiquement
    // rechargé (plus aucune impasse pour l'auteur).
    expect(conteneur.textContent).toContain('révision périmée');
    expect(conteneur.textContent).toContain("atelier rechargé avec l'état à jour");
  });
});

describe('Atelier E5 — FA7 (restitution pédagogique)', () => {
  it('affiche le diff, le badge règle et la trame pédagogique dans le détail — FA7', async () => {
    const etat = etatAtelier('tout');
    etat.document.corrections_barre[0].explication =
      "Cause : le sujet est au pluriel. Règle : le verbe s'accorde avec son sujet. " +
      "Correction : « part » devient « partent ». Effet : l'accord est rétabli.";
    reparerFetch(() => reponseJson(etat));
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    // La première correction active est sélectionnée d'office (réconciliation)
    // → le détail enrichi est visible SANS action de l'auteur.
    // Diff visuel : Fragment d'origine (barré) → Proposition.
    expect(conteneur.textContent).toContain("Fragment d'origine");
    expect(conteneur.textContent).toContain('Proposition');
    expect(conteneur.querySelector('.barre-diff__valeur--origine')).toBeTruthy();
    expect(conteneur.querySelector('.barre-diff__valeur--proposition')).toBeTruthy();
    // Badge / cartouche distinct pour la règle
    expect(conteneur.querySelector('.badge-regle')).toBeTruthy();
    expect(conteneur.textContent).toContain('Accord sujet-verbe');
    // Trame pédagogique en 4 temps (FA5) : Cause → Règle → Correction → Effet
    const temps = Array.from(conteneur.querySelectorAll('.barre-trame dt')).map(
      (d) => d.textContent?.trim(),
    );
    expect(temps).toEqual(['Cause', 'Règle', 'Correction', 'Effet']);
    expect(conteneur.textContent).toContain('le sujet est au pluriel');
    expect(conteneur.textContent).toContain("l'accord est rétabli");
  });

  it('présente le fragment comme « signalé » quand la correction ne réécrit pas — FA7', async () => {
    // Style marque SANS réécrire (original == correction) : pas de diff
    // origine → proposition, mais un fragment mis en valeur.
    reparerFetch(() => reponseJson(etatAtelier('tout')));
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    // Repli brut (explication sans trame) : l'explication reste lisible
    expect(conteneur.textContent).toContain('Le sujet pluriel commande l’accord.');
    // Sélection de la correction Style (c-0002) : fragment signalé, pas de diff
    const lignes = conteneur.querySelectorAll('.barre-ligne');
    (lignes[1] as HTMLElement).click();
    await attendre();
    expect(conteneur.textContent).toContain('Fragment signalé');
    expect(conteneur.querySelector('.barre-diff__valeur--origine')).toBeNull();
  });

  it('sélectionne la ligne de la barre latérale au clic sur une marque — FA7', async () => {
    reparerFetch(() => reponseJson(etatAtelier('tout')));
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    const marque = conteneur.querySelector('[data-groupe="g-0001"]') as HTMLElement;
    marque.click();
    await attendre();

    const ligneActive = conteneur.querySelector('.barre-ligne--active');
    expect(ligneActive).toBeTruthy();
    expect(ligneActive?.textContent).toContain('Forme — accord sujet verbe');
    // La marque active est mise en évidence dans le manuscrit
    expect(conteneur.querySelector('.marque-active')).toBeTruthy();
    // La ligne active défile dans la vue (liaison texte → explication)
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it('rejoint la marque dans le manuscrit depuis la barre latérale (focus) — FA7', async () => {
    reparerFetch(() => reponseJson(etatAtelier('tout')));
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    const lignes = conteneur.querySelectorAll('.barre-ligne');
    (lignes[1] as HTMLElement).click(); // Style — g-0002
    await attendre();

    // Défilement CENTRÉ + FOCUS sur la première marque du groupe
    expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({
      block: 'center',
      behavior: 'smooth',
    });
    const actif = document.activeElement as HTMLElement | null;
    expect(actif?.dataset?.groupe).toBe('g-0002');
  });

  it('affiche une info-bulle au focus d’une marque et la ferme avec Échap — FA7', async () => {
    reparerFetch(() => reponseJson(etatAtelier('tout')));
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    const marque = conteneur.querySelector('button[data-groupe="g-0001"]') as HTMLElement;
    marque.focus();
    await attendre();

    const bulle = conteneur.querySelector('#infobulle-marque');
    expect(bulle).toBeTruthy();
    expect(bulle?.getAttribute('role')).toBe('tooltip');
    // Résumé rapide : titre, règle, diff court
    expect(bulle?.textContent).toContain('Forme — accord sujet verbe');
    expect(bulle?.textContent).toContain('Accord sujet-verbe');
    expect(bulle?.textContent).toContain('partent');

    document.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }),
    );
    await attendre();
    expect(conteneur.querySelector('#infobulle-marque')).toBeNull();
  });

  it('navigue au clavier dans le menu contextuel et restaure le focus — FA7', async () => {
    reparerFetch(() => reponseJson(etatAtelier('tout')));
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    const marque = conteneur.querySelector('button[data-groupe="g-0001"]') as HTMLElement;
    marque.focus();
    marque.dispatchEvent(
      new MouseEvent('contextmenu', { bubbles: true, cancelable: true }),
    );
    await attendre();

    const items = Array.from(
      conteneur.querySelectorAll('[role="menuitem"]'),
    ) as HTMLElement[];
    expect(items.length).toBe(2);
    // FA7 — focus initial sur le premier élément du menu
    expect(document.activeElement).toBe(items[0]);

    // ArrowDown / ArrowUp déplacent le focus d'un item à l'autre
    items[0].dispatchEvent(
      new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }),
    );
    expect(document.activeElement).toBe(items[1]);
    items[1].dispatchEvent(
      new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true }),
    );
    expect(document.activeElement).toBe(items[0]);

    // Échap ferme le menu et RESTAURE le focus sur la marque déclencheuse
    document.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }),
    );
    await attendre();
    expect(conteneur.querySelector('.menu-contextuel')).toBeNull();
    expect(document.activeElement).toBe(marque);
  });

  it('applique une correction Forme depuis le détail (alternative au clic droit) — FA7', async () => {
    reparerFetch((url) => reponseJson(etatAtelier('tout')));
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    // FA7 — alternative accessible (clavier / tactile) : boutons du détail
    // de la barre latérale, sans menu contextuel.
    const boutonAppliquer = Array.from(conteneur.querySelectorAll('button')).find(
      (b) => b.textContent?.includes('Appliquer la correction'),
    );
    expect(boutonAppliquer).toBeTruthy();
    boutonAppliquer?.click();
    await attendre();
    await attendre();

    const appelPost = appelsCaptures().find((a) => a.includes('choix-forme'));
    expect(appelPost).toBeTruthy();
    expect(appelPost).toContain('revision=3');
  });

  it('ouvre le popover de suggestion avec focus piégé et restaure le focus — FA7', async () => {
    reparerFetch((url) => {
      if (url.includes('embellir')) {
        return reponseJson({
          texte: 'Version embellie.',
          explication: 'Cause : rythme. Effet : lecture fluide.',
        });
      }
      return reponseJson(etatAtelier('tout'));
    });
    rendre(Atelier, { analyseId: 7 });
    await attendre();
    await attendre();

    // Sélection dans le paragraphe (simulée via getSelection) — Svelte 5
    // insère des ancres en commentaires autour du texte : on vise le vrai
    // nœud TEXTE du premier segment (nodeType 3), pas firstChild.
    const paragraphe = conteneur.querySelector('.paragraphe') as HTMLElement;
    const spanTexte = paragraphe.querySelector('.seg-texte') as HTMLElement;
    const noeud = Array.from(spanTexte.childNodes).find(
      (n) => n.nodeType === Node.TEXT_NODE && (n.textContent?.length ?? 0) > 0,
    ) as Text;
    const plage = document.createRange();
    plage.setStart(noeud, 0);
    plage.setEnd(noeud, noeud.length);
    const selection = {
      isCollapsed: false,
      rangeCount: 1,
      getRangeAt: () => plage,
    } as unknown as Selection;
    vi.stubGlobal('getSelection', vi.fn(() => selection));

    paragraphe.dispatchEvent(
      new MouseEvent('contextmenu', { bubbles: true, cancelable: true }),
    );
    await attendre();

    const boutonEmbellir = Array.from(conteneur.querySelectorAll('button')).find(
      (b) => b.textContent?.includes('Embellir la sélection'),
    );
    expect(boutonEmbellir).toBeTruthy();
    boutonEmbellir?.click();
    await attendre();
    await attendre();

    const popoverEl = conteneur.querySelector('.popover');
    expect(popoverEl).toBeTruthy();
    expect(popoverEl?.textContent).toContain('Version embellie.');
    // FA7 — focus initial DANS le dialogue (piège de focus)
    expect(popoverEl?.contains(document.activeElement)).toBe(true);

    // Tab depuis le dernier contrôle ramène au premier (piège de focus)
    const boutons = Array.from(
      popoverEl!.querySelectorAll('button'),
    ) as HTMLElement[];
    boutons[boutons.length - 1].focus();
    boutons[boutons.length - 1].dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }),
    );
    expect(document.activeElement).toBe(boutons[0]);

    // Échap ferme le popover
    document.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }),
    );
    await attendre();
    expect(conteneur.querySelector('.popover')).toBeNull();
  });
});