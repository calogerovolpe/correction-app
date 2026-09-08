import { afterEach, describe, expect, it, vi } from 'vitest';

import { api, ErreurApiApp } from '../src/lib/api/client';

function reponseJson(corps: unknown, statut = 200): Response {
  return new Response(JSON.stringify(corps), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('Client API /api/v1 (F0)', () => {
  it('construit la requête et décode le JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      reponseJson({ projet_id: 'P-AB12CD', titre: 'Mon roman', actif: true }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const resultat = await api.obtenir<{ projet_id: string; titre: string; actif: boolean }>(
      '/projets',
    );
    expect(resultat.titre).toBe('Mon roman');
    expect(fetchMock).toHaveBeenCalledOnce();
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain('/api/v1/projets');
  });

  it('lève une ErreurApiApp sur une réponse 500', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(reponseJson({ detail: 'boom' }, 500)),
    );

    await expect(api.obtenir('/projets')).rejects.toBeInstanceOf(ErreurApiApp);
  });

  it('lève une ErreurApiApp sur une panne réseau', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')));

    await expect(api.obtenir('/projets')).rejects.toBeInstanceOf(ErreurApiApp);
  });
});