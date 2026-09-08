import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  activerProjet,
  analysesRecentes,
  creerProjet,
  listerProjets,
  supprimerProjet,
} from '../src/lib/api/projets';

function reponseJson(corps: unknown, statut = 200): Response {
  return new Response(JSON.stringify(corps), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('Module API projets (F1)', () => {
  it('listerProjets appelle GET /api/v1/projets', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: RequestInfo | URL) => {
        expect(String(url)).toContain('/api/v1/projets');
        return reponseJson({ projets: [] });
      }),
    );
    const resultat = await listerProjets();
    expect(resultat.projets).toEqual([]);
  });

  it('creerProjet envoie le titre en JSON', async () => {
    let corpsRecu = '';
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: RequestInfo | URL, options: RequestInit = {}) => {
        expect(String(url)).toContain('/api/v1/projets');
        expect(options.method).toBe('POST');
        corpsRecu = String(options.body);
        return reponseJson(
          {
            projet_id: 'P-ABABAB',
            titre: 'Mon roman',
            actif: true,
            chain_status: 'vierge',
            current_chapter_num: null,
            last_chapter_title: null,
            created_at: '2026-09-09 12:00:00',
          },
          201,
        );
      }),
    );
    const projet = await creerProjet('Mon roman');
    expect(projet.projet_id).toBe('P-ABABAB');
    expect(JSON.parse(corpsRecu)).toEqual({ titre: 'Mon roman' });
  });

  it('activerProjet appelle POST /api/v1/projets/{id}/activer', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: RequestInfo | URL) => {
        expect(String(url)).toContain('/api/v1/projets/P-ABCDEF/activer');
        return new Response(null, { status: 204 });
      }),
    );
    await expect(activerProjet('P-ABCDEF')).resolves.toBeUndefined();
  });

  it('supprimerProjet appelle DELETE /api/v1/projets/{id}', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: RequestInfo | URL) => {
        expect(String(url)).toContain('/api/v1/projets/P-ABCDEF');
        return new Response(null, { status: 204 });
      }),
    );
    await expect(supprimerProjet('P-ABCDEF')).resolves.toBeUndefined();
  });

  it('analysesRecentes appelle GET /api/v1/analyses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: RequestInfo | URL) => {
        expect(String(url)).toContain('/api/v1/analyses');
        return reponseJson({
          analyses: [
            {
              id: 3,
              statut: 'terminee',
              categorie: 'chapitre',
              extrait: 'Il faisait beau',
              cree_a: '2026-09-09 08:00:00',
            },
          ],
        });
      }),
    );
    const { analyses } = await analysesRecentes();
    expect(analyses).toHaveLength(1);
    expect(analyses[0].statut).toBe('terminee');
  });
});