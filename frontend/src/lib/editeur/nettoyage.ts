/** Nettoyage Word strict au collage + sérialisation v2 (jalon F2, E3).
 *
 *  Logique EXACTE du script de `app/templates/analyses/nouveau.html` (J2.2),
 *  extraite en fonctions pures testables pour le composant Svelte
 *  `EditeurWord` : nettoyage HTML (métadonnées Word, classes, styles, feuilles
 *  de blocs), repli texte brut par lignes, sérialisation au format v2
 *  attendu par `texte_riche.parser_document_riche` :
 *  `[{ id: "p-N", runs: [{ texte, gras, italique, souligne }] }]`.
 */

export interface RunRiche {
  texte: string;
  gras: boolean;
  italique: boolean;
  souligne: boolean;
}

export interface ParagrapheRiche {
  id: string;
  runs: RunRiche[];
}

const TAGS_BLOC = 'p, h1, h2, h3, h4, div';

/** Crée une racine HTML pour le nettoyage : DOMParser (navigateur) sinon un
 *  conteneur `div` (jsdom) — API DOM identique sur l'élément racine. */
function creerRacine(html: string): HTMLElement {
  if (typeof DOMParser !== 'undefined') {
    return new DOMParser().parseFromString(html, 'text/html').body;
  }
  const conteneur = document.createElement('div');
  conteneur.innerHTML = html;
  return conteneur;
}

/** Nettoie le HTML Word d'un collage et retourne des `<p>` simples (sans
 *  classes ni styles), prêts à être insérés dans l'éditeur contenteditable.
 *  Retourne une liste vide si aucune feuille textuelle n'est exploitable. */
export function nettoyerHtmlWord(html: string): HTMLParagraphElement[] {
  const racine = creerRacine(html);

  // 1. Supprimer les éléments Word non textuels et métadonnées
  racine.querySelectorAll('xml, style, script, meta, link').forEach((el) => el.remove());

  racine.querySelectorAll('*').forEach((el) => {
    if (el.tagName.toLowerCase().includes(':')) el.remove();
    el.removeAttribute('class');
    el.removeAttribute('style');
    el.removeAttribute('lang');
  });

  // 2. Extraire les paragraphes terminaux (feuilles) pour éviter d'imbriquer div + p
  const candidats = Array.from(racine.querySelectorAll(TAGS_BLOC));
  const feuilles = candidats.filter(
    (el) => el.querySelector(TAGS_BLOC) === null,
  );

  const propres: HTMLParagraphElement[] = [];
  if (feuilles.length > 0) {
    for (const feuille of feuilles) {
      // Insécables : certains navigateurs les maintiennent en entité `&nbsp;`,
      // d'autres les décodent déjà en U+00A0 (jsdom) — les deux sont ramenés
      // à une espace simple (fidélité du compteur et du texte soumis).
      const interieur = feuille.innerHTML.replace(/&nbsp;/g, ' ').replace(/\u00A0/g, ' ').trim();
      if (interieur && interieur !== '<br>') {
        const p = document.createElement('p');
        p.innerHTML = feuille.innerHTML;
        propres.push(p);
      }
    }
  }
  return propres;
}

/** Repli texte brut (pas de HTML au presse-papiers) : chaque ligne non vide
 *  devient un paragraphe — fidèle au comportement Word-fidèle actuel. */
export function insererTexteLignes(texte: string): HTMLParagraphElement[] {
  const lignes = texte.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  const paragraphes: HTMLParagraphElement[] = [];
  for (const ligne of lignes) {
    const nettoiee = ligne.trim();
    if (nettoiee) {
      const p = document.createElement('p');
      p.textContent = nettoiee;
      paragraphes.push(p);
    }
  }
  return paragraphes;
}

/** Parcourt un nœud en portant le formatage (gras/italique/souligné). */
function explorerNoeud(
  noeud: Node,
  gras: boolean,
  italique: boolean,
  souligne: boolean,
  runs: RunRiche[],
  texteBloc: string[],
): void {
  if (noeud.nodeType === Node.TEXT_NODE) {
    const t = noeud.textContent ?? '';
    if (t) {
      runs.push({ texte: t, gras, italique, souligne });
      texteBloc.push(t);
    }
  } else if (noeud.nodeType === Node.ELEMENT_NODE) {
    const el = noeud as HTMLElement;
    const tag = el.tagName;
    const estGras = gras || tag === 'B' || tag === 'STRONG';
    const estItalique = italique || tag === 'I' || tag === 'EM';
    const estSouligne = souligne || tag === 'U';
    for (const enfant of Array.from(el.childNodes)) {
      explorerNoeud(enfant, estGras, estItalique, estSouligne, runs, texteBloc);
    }
  }
}

/** Sérialise un éditeur contenteditable en paragraphes v2 + texte brut complet
 *  (pour le compteur). Les paragraphes vides de pur espace sont ignorés ; les
 *  ids sont renumérotés séquentiellement p-1, p-2… (règle du backend). */
export function serialiserEditeur(
  editeur: HTMLElement,
): { paragraphes: ParagrapheRiche[]; texte: string } {
  if (!editeur) return { paragraphes: [], texte: '' };
  const childNodes = Array.from(editeur.childNodes);
  if (childNodes.length === 0) return { paragraphes: [], texte: '' };

  // Regrouper par bloc (chaque P/DIV ou série de nœuds en ligne séparée par BR)
  const blocs: Node[][] = [];
  let blocCourant: Node[] = [];
  for (const node of childNodes) {
    if (node.nodeType === Node.ELEMENT_NODE && (node.nodeName === 'P' || node.nodeName === 'DIV')) {
      if (blocCourant.length > 0) {
        blocs.push(blocCourant);
        blocCourant = [];
      }
      blocs.push([node as HTMLElement]);
    } else if (node.nodeType === Node.ELEMENT_NODE && node.nodeName === 'BR') {
      if (blocCourant.length > 0) {
        blocs.push(blocCourant);
        blocCourant = [];
      }
    } else {
      // Espace entre deux balises blocs : ignoré pour ne pas créer de paragraphe fantôme
      const estEspace = node.nodeType === Node.TEXT_NODE && !(node.textContent ?? '').trim();
      if (!estEspace) blocCourant.push(node);
    }
  }
  if (blocCourant.length > 0) blocs.push(blocCourant);

  const paragraphes: ParagrapheRiche[] = [];
  let texteBrutTotal = '';
  let pIndex = 1;

  for (const bloc of blocs) {
    const runs: RunRiche[] = [];
    const morceaux: string[] = [];
    for (const node of bloc) {
      explorerNoeud(node, false, false, false, runs, morceaux);
    }
    const texteBloc = morceaux.join('');
    // Ne retenir que les paragraphes ayant un contenu textuel réel (trim non vide)
    if (texteBloc.trim().length > 0) {
      paragraphes.push({ id: `p-${pIndex++}`, runs });
      texteBrutTotal += texteBloc.trim() + '\n';
    }
  }

  return { paragraphes, texte: texteBrutTotal.trim() };
}

/** Nombre de caractères du texte soumis (compteur E3) — le refus au-delà de
 *  `max_caracteres` est explicite, jamais de troncature silencieuse. */
export function compterCaracteres(texte: string): number {
  return texte.length;
}