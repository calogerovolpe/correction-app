import { describe, expect, it } from 'vitest';

import { decouperTrame, premierePhrase } from '../src/lib/pedagogie';

/** FA7 — Restitution pédagogique : la trame Cause → Règle → Correction →
 *  Effet (générée depuis le jalon FA5) est découpée pour l'affichage enrichi
 *  de la barre latérale ; tout format non conforme → repli brut (null). */

describe('decouperTrame (FA7)', () => {
  it('découpe une explication conforme à la trame en 4 temps', () => {
    const trame = decouperTrame(
      "Cause : le sujet est au pluriel. Règle : le verbe s'accorde avec son sujet. " +
        "Correction : « part » devient « partent ». Effet : l'accord est rétabli.",
    );
    expect(trame).not.toBeNull();
    expect(trame?.cause).toBe('le sujet est au pluriel');
    expect(trame?.regle).toBe("le verbe s'accorde avec son sujet");
    expect(trame?.correction).toBe('« part » devient « partent »');
    expect(trame?.effet).toBe("l'accord est rétabli");
  });

  it('tolère l\'accent de « Règle » et un préambule avant la trame', () => {
    const trame = decouperTrame(
      "Ici le verbe pose problème. Cause : le sujet est pluriel. Regle : accord verbe. " +
        "Correction : partir → partent. Effet : phrase correcte.",
    );
    expect(trame).not.toBeNull();
    expect(trame?.cause).toContain('sujet est pluriel');
    expect(trame?.regle).toBe('accord verbe');
  });

  it('accepte une trame partielle (cause + effet, suggestions)', () => {
    const trame = decouperTrame(
      "Cause : répétition rapprochée. Effet : le rythme s'alourdit.",
    );
    expect(trame).not.toBeNull();
    expect(trame?.cause).toBe('répétition rapprochée');
    expect(trame?.regle).toBe('');
    expect(trame?.correction).toBe('');
    expect(trame?.effet).toBe("le rythme s'alourdit");
  });

  it('retourne null pour une explication sans trame (repli brut)', () => {
    expect(decouperTrame('Le sujet pluriel commande l’accord.')).toBeNull();
    expect(decouperTrame('')).toBeNull();
  });

  it('retourne null si les intitulés sont hors ordre canonique', () => {
    expect(
      decouperTrame('Effet : tard. Cause : tôt. Correction : rien.'),
    ).toBeNull();
  });
});

describe('premierePhrase (FA7)', () => {
  it('renvoie la première phrase pour le résumé de l\'info-bulle', () => {
    expect(
      premierePhrase('Première phrase. Deuxième phrase ! Troisième ?'),
    ).toBe('Première phrase.');
  });

  it('gère une explication sans ponctuation finale', () => {
    expect(premierePhrase('Un seul fragment')).toBe('Un seul fragment');
  });
});