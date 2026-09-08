<script lang="ts">
  import {
    insererTexteLignes,
    nettoyerHtmlWord,
    serialiserEditeur,
  } from '../editeur/nettoyage';

  /** Éditeur Word-fidèle (E3, jalon F2) : contenteditable avec collage Word
   *  strictement nettoyé (gras/italique/souligné préservés, paragraphes),
   *  barre d'outils G/I/S, et sérialisation continue au format v2 via les
   *  bindables `valeur` (JSON) et `compteur` (caractères). */

  interface Props {
    valeur?: string;
    compteur?: number;
  }

  let { valeur = $bindable(''), compteur = $bindable(0) }: Props = $props();
  let editeur: HTMLDivElement | undefined = $state();

  function appliquerCommande(commande: 'bold' | 'italic' | 'underline'): void {
    if (!editeur) return;
    editeur.focus();
    document.execCommand(commande, false);
    mettreAJour();
  }

  function coller(evenement: ClipboardEvent): void {
    evenement.preventDefault();
    const donnees = evenement.clipboardData;
    if (!editeur || !donnees) return;
    const html = donnees.getData('text/html') ?? '';
    const texte = donnees.getData('text/plain') ?? '';

    let paragraphes: HTMLParagraphElement[] = [];
    if (html) {
      paragraphes = nettoyerHtmlWord(html);
      if (paragraphes.length === 0 && texte) {
        paragraphes = insererTexteLignes(texte);
      }
    } else if (texte) {
      paragraphes = insererTexteLignes(texte);
    }

    editeur.innerHTML = '';
    for (const p of paragraphes) editeur.appendChild(p);
    mettreAJour();
  }

  function mettreAJour(): void {
    if (!editeur) {
      valeur = '';
      compteur = 0;
      return;
    }
    const resultat = serialiserEditeur(editeur);
    valeur = resultat.paragraphes.length > 0 ? JSON.stringify(resultat.paragraphes) : '';
    compteur = resultat.texte.length;
  }
</script>

<div class="editeur-word-bloc">
  <div class="editeur-word-barre">
    <button type="button" class="bouton-outil" onclick={() => appliquerCommande('bold')} aria-label="Gras">
      <strong>G</strong>
    </button>
    <button type="button" class="bouton-outil" onclick={() => appliquerCommande('italic')} aria-label="Italique">
      <em>I</em>
    </button>
    <button type="button" class="bouton-outil" onclick={() => appliquerCommande('underline')} aria-label="Souligné">
      <u>S</u>
    </button>
    <span class="editeur-word-info">
      Collez depuis Word : les sauts de lignes et styles (gras, italique,
      souligné) sont nettoyés et préservés fidèlement.
    </span>
  </div>

  <div
    class="editeur-word manuscrit"
    contenteditable="true"
    role="textbox"
    aria-multiline="true"
    aria-label="Zone de texte de votre manuscrit"
    bind:this={editeur}
    oninput={mettreAJour}
    onpaste={coller}
  ></div>
</div>

<style>
  .editeur-word-bloc {
    display: grid;
    gap: 0.5rem;
  }
  .editeur-word-barre {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .bouton-outil {
    font: inherit;
    line-height: 1.2;
    min-width: 2.2rem;
    padding: 0.3rem 0.55rem;
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    background: var(--fond-surface);
    color: var(--encre);
    cursor: pointer;
  }
  .bouton-outil:hover {
    background: var(--accent-doux);
    border-color: var(--accent);
  }
  .editeur-word-info {
    font-size: 0.9rem;
    color: var(--encre-douce);
  }
  .editeur-word {
    min-height: 14rem;
    padding: 0.75rem;
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    background: var(--fond-surface);
    color: var(--encre);
    white-space: pre-wrap;
  }
  .editeur-word:focus {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }
</style>