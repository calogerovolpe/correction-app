import { describe, expect, it } from 'vitest';

import {
  compterCaracteres,
  insererTexteLignes,
  nettoyerHtmlWord,
  serialiserEditeur,
} from '../src/lib/editeur/nettoyage';

/** Logique du collage Word + sérialisation v2 (jalon F2, E3) : la fidélité du
 *  texte soumis dépend de ces fonctions pures — elles doivent rester
 *  identiques au comportement actuel de l'éditeur Jinja2 (nouveau.html). */

describe('nettoyerHtmlWord (collage Word fidèle)', () => {
  it('retire les métadonnées Word et nettoie classes/styles/lang', () => {
    const html =
      '<html xmlns:o="urn:schemas-microsoft-com:office:office">' +
      '<head><style>p { color: red }</style></head>' +
      '<body><p class="MsoNormal" style="margin:0"><o:p></o:p>Premier paragraphe</p></body></html>';
    const propres = nettoyerHtmlWord(html);
    expect(propres).toHaveLength(1);
    expect(propres[0].textContent).toBe('Premier paragraphe');
    expect(propres[0].getAttribute('class')).toBeNull();
    expect(propres[0].getAttribute('style')).toBeNull();
  });

  it('préserve le gras au collage (les insécables restants restent fidèles)', () => {
    const html = '<p>Un&nbsp;mot <b>important</b></p><div><p>Second</p></div>';
    const propres = nettoyerHtmlWord(html);
    expect(propres).toHaveLength(2);
    // Les insécables du texte collé sont préservés (fidélité Word) ; la
    // feuille « Second » est bien détectée malgré le div englobant.
    expect(propres[0].textContent).toBe('Un\u00A0mot important');
    expect(propres[1].textContent).toBe('Second');
    expect(propres[0].querySelector('b')).not.toBeNull();
  });

  it('ignore les feuilles vides ou de pur espace', () => {
    const propres = nettoyerHtmlWord('<p>Texte</p><p><br></p><p>   </p>');
    expect(propres).toHaveLength(1);
    expect(propres[0].textContent).toBe('Texte');
  });
});

describe('insererTexteLignes (repli texte brut)', () => {
  it('crée un paragraphe par ligne non vide, bordure nettoyée', () => {
    const paragraphes = insererTexteLignes('Ligne un\n\n  Ligne deux  \r\nTrois');
    expect(paragraphes.map((p) => p.textContent)).toEqual(['Ligne un', 'Ligne deux', 'Trois']);
  });

  it('retourne une liste vide pour un texte vide', () => {
    expect(insererTexteLignes('')).toEqual([]);
    expect(insererTexteLignes('\n\n  \n')).toEqual([]);
  });
});

describe('serialiserEditeur (format v2 attendu par le backend)', () => {
  it('produit les paragraphes p-1, p-2… avec leurs runs formatés', () => {
    const editeur = document.createElement('div');
    editeur.innerHTML =
      '<p>Les cavaliers <b>partent</b> à l\u2019aube.</p>' +
      '<p>   </p>' +
      '<p><i>Sans</i> emphase.</p>';

    const resultat = serialiserEditeur(editeur);

    // Le paragraphe de pur espace est ignoré (même règle que le backend)
    expect(resultat.paragraphes).toHaveLength(2);
    expect(resultat.paragraphes[0].id).toBe('p-1');
    expect(resultat.paragraphes[1].id).toBe('p-2');

    const runs = resultat.paragraphes[0].runs;
    expect(runs[0]).toEqual({ texte: 'Les cavaliers ', gras: false, italique: false, souligne: false });
    expect(runs[1]).toEqual({ texte: 'partent', gras: true, italique: false, souligne: false });

    expect(resultat.paragraphes[1].runs[0]).toEqual({
      texte: 'Sans',
      gras: false,
      italique: true,
      souligne: false,
    });
  });

  it('concatène le texte brut pour le compteur (trim de la concaténation)', () => {
    const editeur = document.createElement('div');
    editeur.innerHTML = '<p>Premier</p><p>Second paragraphe</p>';

    const resultat = serialiserEditeur(editeur);
    expect(resultat.texte).toBe('Premier\nSecond paragraphe');
    expect(compterCaracteres(resultat.texte)).toBe('Premier\nSecond paragraphe'.length);
  });

  it('retourne un état vide pour un éditeur sans contenu', () => {
    const editeur = document.createElement('div');
    const resultat = serialiserEditeur(editeur);
    expect(resultat.paragraphes).toEqual([]);
    expect(resultat.texte).toBe('');
  });
});