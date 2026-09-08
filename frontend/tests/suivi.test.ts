import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mount, unmount } from 'svelte';
import type { Component } from 'svelte';

import Suivi from '../src/routes/Suivi.svelte';

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
const attendrePendant = (ms: number) => new Promise((resoudre) => setTimeout(resoudre, ms));

function reponseJson(corps: unknown, statut = 200): Response {
  return new Response(JSON.stringify(corps), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

function reponseSuivi(
  statut: string,
  erreur: string | null = null,
  etape: string | null = null,
  resultat: unknown = null,
): Response {
  return reponseJson({
    id: 7,
    statut,
    etape,
    erreur,
    categorie: 'chapitre',
    cree_a: '2026-09-09 10:00:00',
    fini_a: null,
    resultat,
  });
}

/** Remplace `fetch` : la fabrique reçoit le numéro d'appel courant (1, 2, …)
 *  et retourne la réponse HTTP simulée. Retourne un compteur d'appels
 *  (pour vérifier l'arrêt du polling à l'état final). */
function reparerFetch(fabrique: (appel: number) => Response): { appels: () => number } {
  let n = 0;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: RequestInfo | URL) => {
      n++;
      expect(String(url)).toContain('/api/v1/analyses/7');
      return fabrique(n);
    }),
  );
  return { appels: () => n };
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

describe('Suivi E4 (F2)', () => {
  it('suit en_attente → en_cours → terminee puis arrête le polling', async () => {
    const filets = reparerFetch((appel) => {
      if (appel === 1) return reponseSuivi('en_attente');
      if (appel === 2) return reponseSuivi('en_cours', null, 'phases');
      return reponseSuivi('terminee', null, null, { nb_corrections: 1, par_phase: { forme: 1 } });
    });
    rendre(Suivi, { analyseId: 7, periodePolling: 20 });
    await attendrePendant(140);

    expect(conteneur.textContent).toContain('Terminée');
    expect(conteneur.textContent).toContain('1 correction(s) active(s)');
    expect(conteneur.textContent).toContain('Ouvrir le résultat');

    // Le polling s'arrête à l'état final : plus aucun appel ensuite
    const final = filets.appels();
    await attendrePendant(80);
    expect(filets.appels()).toBe(final);
  });

  it('affiche un succès direct quand le job est déjà terminé (Extrait)', async () => {
    reparerFetch(() => reponseSuivi('terminee', null, null, { nb_corrections: 2, par_phase: { forme: 2 } }));
    rendre(Suivi, { analyseId: 7, periodePolling: 20 });
    await attendrePendant(60);

    expect(conteneur.textContent).toContain('Terminée');
    expect(conteneur.textContent).toContain('Forme');
  });

  it('affiche le refus fail-fast (rejetee) avec l\u2019erreur verbatim', async () => {
    reparerFetch(() =>
      reponseSuivi(
        'rejetee',
        '⛔ Exécution interrompue — la phase forme ne répond pas (modèle indisponible).',
      ),
    );
    rendre(Suivi, { analyseId: 7, periodePolling: 20 });
    await attendrePendant(60);

    expect(conteneur.textContent).toContain('Refusée');
    expect(conteneur.textContent).toContain('la phase forme ne répond pas');
  });

  it('affiche l\u2019échec Option B sans résultat partiel', async () => {
    reparerFetch(() =>
      reponseSuivi(
        'echec',
        '⛔ Exécution interrompue — la phase style a échoué en cours d\u2019analyse. Aucun document n\u2019a été émis.',
      ),
    );
    rendre(Suivi, { analyseId: 7, periodePolling: 20 });
    await attendrePendant(60);

    expect(conteneur.textContent).toContain('Échec');
    expect(conteneur.textContent).toContain('la phase style a échoué en cours d\u2019analyse');
    expect(conteneur.textContent).not.toContain('Ouvrir le résultat');
  });

  it('affiche un bandeau si l\u2019analyse est introuvable (404)', async () => {
    reparerFetch(() => reponseJson({ detail: 'Analyse introuvable.' }, 404));
    rendre(Suivi, { analyseId: 7, periodePolling: 20 });
    await attendrePendant(60);

    expect(conteneur.textContent).toContain('Analyse introuvable.');
    expect(conteneur.textContent).toContain('Revenir à la soumission');
  });

  it('ne fabrique jamais de statut fantôme : statut inconnu → erreur', async () => {
    reparerFetch(() => reponseSuivi('en_attente_et_rangee'));
    rendre(Suivi, { analyseId: 7, periodePolling: 20 });
    await attendrePendant(60);

    expect(conteneur.textContent).toContain('non reconnu');
    expect(conteneur.textContent).not.toContain('deux secondes');
  });
});