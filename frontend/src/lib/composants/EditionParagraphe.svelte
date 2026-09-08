<script lang="ts">
  import Bouton from './Bouton.svelte';

  /** Édition DIRECTE sans IA temps réel (UX4, décision 38) : un paragraphe du
   *  texte affiché est édité en textarea ; « Enregistrer » crée un patch ancré
   *  base, « ↻ Re-corriger » (action de l'atelier) relance le pipeline. */

  interface Props {
    texte: string;
    onchange: (texte: string) => void;
    onvalider: () => void;
    onannuler: () => void;
  }

  let { texte, onchange, onvalider, onannuler }: Props = $props();

  let valeurLocale = $state('');

  // Garde la zone d'édition synchronisée avec le texte affiché du paragraphe
  // (référencée dans une closure pour rester réactive à la prop).
  $effect(() => {
    valeurLocale = texte;
  });
</script>

<div class="edition-paragraphe">
  <textarea
    class="edition-paragraphe__zone"
    rows="6"
    aria-label="Texte du paragraphe à éditer"
    bind:value={valeurLocale}
    oninput={() => onchange(valeurLocale)}
  ></textarea>
  <p class="edition-paragraphe__aide">
    L'édition est enregistrée telle quelle (aucune IA en temps réel). Utilisez
    « ↻ Re-corriger » pour relancer l'analyse de ce texte.
  </p>
  <div class="edition-paragraphe__actions">
    <Bouton variante="primaire" onclick={() => onvalider()}>Enregistrer</Bouton>
    <Bouton variante="secondaire" onclick={() => onannuler()}>Annuler</Bouton>
  </div>
</div>

<style>
  .edition-paragraphe {
    display: grid;
    gap: 0.5rem;
    margin: 0.25rem 0;
  }
  .edition-paragraphe__zone {
    width: 100%;
    font-family: var(--police-manuscrit);
    font-size: 1.05rem;
    line-height: 1.6;
    padding: 0.6rem;
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    background: var(--fond-surface);
    color: var(--encre);
    resize: vertical;
  }
  .edition-paragraphe__zone:focus {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }
  .edition-paragraphe__aide {
    margin: 0;
    font-size: 0.82rem;
    color: var(--encre-douce);
  }
  .edition-paragraphe__actions {
    display: flex;
    gap: 0.6rem;
  }
</style>