import type { ErreurApi } from './types';

/** Client fetch typé pour l'API JSON /api/v1/ (jalon F0).
 *  Local-first : aucun CDN, aucune dépendance. Mis en service à partir de F1
 *  (projets, analyses) ; le serveur n'expose pas encore /api/v1/ — ce module
 *  est prêt mais non branché. */

export class ErreurApiApp extends Error {
  readonly statut: number;

  constructor(message: string, statut: number) {
    super(message);
    this.name = 'ErreurApiApp';
    this.statut = statut;
  }
}

type Methode = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

interface OptionsRequete {
  methode?: Methode;
  corps?: unknown;
  parametres?: Record<string, string | number | boolean | undefined>;
}

const BASE_API = '/api/v1';

function construireUrl(chemin: string, parametres?: OptionsRequete['parametres']): string {
  const url = new URL(`${BASE_API}${chemin}`, window.location.origin);
  for (const [cle, valeur] of Object.entries(parametres ?? {})) {
    if (valeur !== undefined && valeur !== '') {
      url.searchParams.set(cle, String(valeur));
    }
  }
  return url.toString();
}

async function requete<T>(chemin: string, options: OptionsRequete = {}): Promise<T> {
  const { methode = 'GET', corps, parametres } = options;
  const enTetes: Record<string, string> = { Accept: 'application/json' };
  if (corps !== undefined) {
    enTetes['Content-Type'] = 'application/json';
  }

  let reponse: Response;
  try {
    reponse = await fetch(construireUrl(chemin, parametres), {
      method: methode,
      headers: enTetes,
      body: corps === undefined ? undefined : JSON.stringify(corps),
    });
  } catch {
    throw new ErreurApiApp('Impossible de joindre le serveur.', 0);
  }

  if (!reponse.ok) {
    let detail = '';
    try {
      const donnees = (await reponse.json()) as ErreurApi;
      detail = donnees.detail ?? donnees.message ?? '';
    } catch {
      // Réponse d'erreur non JSON : seul le statut HTTP est exploitable.
    }
    throw new ErreurApiApp(detail || `Erreur serveur (${reponse.status}).`, reponse.status);
  }

  if (reponse.status === 204) {
    return undefined as T;
  }
  return (await reponse.json()) as T;
}

export interface ClientApi {
  obtenir<T>(chemin: string, parametres?: OptionsRequete['parametres']): Promise<T>;
  envoyer<T>(
    chemin: string,
    corps?: unknown,
    parametres?: OptionsRequete['parametres'],
  ): Promise<T>;
  remplacer<T>(chemin: string, corps?: unknown): Promise<T>;
  modifier<T>(chemin: string, corps?: unknown): Promise<T>;
  supprimer<T>(chemin: string): Promise<T>;
}

export const api: ClientApi = {
  obtenir: (chemin, parametres) => requete(chemin, { parametres }),
  envoyer: (chemin, corps, parametres) =>
    requete(chemin, { methode: 'POST', corps, parametres }),
  remplacer: (chemin, corps) => requete(chemin, { methode: 'PUT', corps }),
  modifier: (chemin, corps) => requete(chemin, { methode: 'PATCH', corps }),
  supprimer: (chemin) => requete(chemin, { methode: 'DELETE' }),
};