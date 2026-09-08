import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  preparerSoumission,
  soumettreAnalyse,
  statutAnalyse,
} from '../src/lib/api/analyses';

function reponseJson(corps: unknown, statut = 200): Response {
  return new Response(JSON.stringify(corps), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('Module API analyses (F2)', () => {
  it('preparerSoumission appelle GET /api/v1/soumission', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: RequestInfo | URL) => {
        expect(String(url)).toContain('/api/v1/soumission');
        return reponseJson({
          projet: null,
          numero_attendu: 0,
          prefil: { categorie: 'chapitre', phases: { forme: true, style: true, technique: true } },
          max_caracteres: 30000,
        });
      }),
    );
    const donnees = await preparerSoumission();
    expect(donnees.numero_attendu).toBe(0);
    expect(donnees.max_caracteres).toBe(30000);
  });

  it('soumettreAnalyse envoie le corps attendu en JSON', async () => {
    let corpsRecu = '';
    let methodeRecue = '';
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: RequestInfo | URL, options: RequestInit = {}) => {
        expect(String(url)).toContain('/api/v1/analyses');
        methodeRecue = String(options.method);
        corpsRecu = String(options.body);
        return reponseJson(
          { id: 3, statut: 'en_attente', etape: null, erreur: null, categorie: null, cree_a: 'x', fini_a: null, resultat: null },
          201,
        );
      }),
    );
    const suivi = await soumettreAnalyse({
      texte: '[{"id":"p-1","runs":[{"texte":"Bonjour","gras":false,"italique":false,"souligne":false}]}]',
      categorie: 'chapitre',
      numero_chapitre: 4,
      avec_codex: true,
      phases: { forme: true, style: true, technique: true },
    });
    expect(methodeRecue).toBe('POST');
    expect(JSON.parse(corpsRecu)).toEqual({
      texte: '[{"id":"p-1","runs":[{"texte":"Bonjour","gras":false,"italique":false,"souligne":false}]}]',
      categorie: 'chapitre',
      numero_chapitre: 4,
      avec_codex: true,
      phases: { forme: true, style: true, technique: true },
    });
    expect(suivi.id).toBe(3);
    expect(suivi.statut).toBe('en_attente');
  });

  it('statutAnalyse appelle GET /api/v1/analyses/{id}', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: RequestInfo | URL) => {
        expect(String(url)).toContain('/api/v1/analyses/7');
        return reponseJson({
          id: 7,
          statut: 'terminee',
          etape: null,
          erreur: null,
          categorie: 'chapitre',
          cree_a: '2026-09-09 10:00:00',
          fini_a: '2026-09-09 10:00:05',
          resultat: { nb_corrections: 2, par_phase: { forme: 2 } },
        });
      }),
    );
    const suivi = await statutAnalyse(7);
    expect(suivi.statut).toBe('terminee');
    expect(suivi.resultat?.par_phase).toEqual({ forme: 2 });
  });
});