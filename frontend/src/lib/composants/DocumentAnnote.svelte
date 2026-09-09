<script lang="ts">
  import type { ParagrapheAnnote, SegmentAnnote, SegmentTexte } from '../api/types';
  import EditionParagraphe from './EditionParagraphe.svelte';

  /** Document annoté (F3) : rendu des paragraphes en couches superposables
   *  (Forme del/ins rouge, Style pointillés bleus, Technique fond jaune,
   *  Embellissement vert), navigation clavier ←/→ entre marques, et édition
   *  DIRECTE d'un paragraphe (mode édition — aucun LLM temps réel). */

  interface Props {
    paragraphes: ParagrapheAnnote[];
    enEditionId: string | null;
    texteEdition: string;
    onSelectionnerGroupe: (groupe: string) => void;
    onDemanderEdition: (paragrapheId: string) => void;
    onDemanderReevaluer: (paragrapheId: string) => void;
    onEditionChange: (texte: string) => void;
    onValiderEdition: () => void;
    onAnnulerEdition: () => void;
  }

  let {
    paragraphes,
    enEditionId,
    texteEdition,
    onSelectionnerGroupe,
    onDemanderEdition,
    onDemanderReevaluer,
    onEditionChange,
    onValiderEdition,
    onAnnulerEdition,
  }: Props = $props();

  /** Navigation clavier ←/→ entre les marques [data-groupe] VISIBLES. */
  function naviguerClavier(evenement: KeyboardEvent): void {
    if (evenement.key !== 'ArrowRight' && evenement.key !== 'ArrowLeft') return;
    const conteneur = document.getElementById('document-annote');
    if (!conteneur) return;
    const cibles = Array.from(
      conteneur.querySelectorAll<HTMLElement>('[data-groupe]'),
    ).filter((el) => el.offsetParent !== null);
    if (cibles.length === 0) return;
    const actif = document.activeElement as HTMLElement | null;
    let index = actif ? cibles.indexOf(actif) : -1;
    if (index === -1) {
      index = evenement.key === 'ArrowRight' ? 0 : cibles.length - 1;
    } else {
      index =
        (index + (evenement.key === 'ArrowRight' ? 1 : -1) + cibles.length) %
        cibles.length;
    }
    evenement.preventDefault();
    cibles[index].focus();
    cibles[index].click();
  }
function segmentTexte(s: SegmentAnnote): SegmentTexte {
    return s as SegmentTexte;
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div id="document-annote" class="document-annote" onkeydown={naviguerClavier}>
  {#each paragraphes as p (p.id)}
    <p class="paragraphe" data-paragraphe-id={p.id}>
      {#if enEditionId === p.id}
        <EditionParagraphe
          texte={texteEdition}
          onchange={onEditionChange}
          onvalider={onValiderEdition}
          onannuler={onAnnulerEdition}
        />
      {:else}
        {#each p.segments as s, index (`${p.id}-${index}-${s.type}`)}
          {@render segmenter(s)}
        {/each}
        {#if p.edite}
          <span class="actions-paragraphe">
            <button
              type="button"
              class="lien-action"
              onclick={() => onDemanderEdition(p.id)}
            >
              Modifier le texte
            </button>
            <button
              type="button"
              class="lien-action"
              onclick={() => onDemanderReevaluer(p.id)}
            >
              ↻ Re-corriger ce paragraphe
            </button>
          </span>
        {/if}
      {/if}
    </p>
  {/each}
  {#if paragraphes.length === 0}
    <p class="aucune-correction">
      Aucune correction détectée — le texte est ressorti propre des phases
      actives.
    </p>
  {/if}
</div>

{#snippet segmenter(s: SegmentAnnote)}
  {#if s.type === 'forme'}
    <del class="del {s.classes}" data-groupe={s.groupe}>{s.del}</del>
    <button
      type="button"
      class="ins ins--forme {s.classes}"
      data-groupe={s.groupe}
      onclick={() => onSelectionnerGroupe(s.groupe)}
    >
      {s.ins}
    </button>
  {:else if segmentTexte(s).groupe}
    <button
      type="button"
      class="seg-texte {segmentTexte(s).classes}"
      data-groupe={segmentTexte(s).groupe}
      onclick={() => onSelectionnerGroupe(segmentTexte(s).groupe!)}
    >
      {segmentTexte(s).texte}
    </button>
  {:else}
    <span class="seg-texte {segmentTexte(s).classes}">{segmentTexte(s).texte}</span>
  {/if}
{/snippet}

<style>
  /* Les marques cliquables sont de vrais <button> (a11y) : reset complet pour
     qu'ils se fondent dans le texte manuscrit. */
  button.ins,
  button.seg-texte {
    border: none;
    padding: 0 2px;
    font: inherit;
    color: inherit;
    cursor: pointer;
    background: transparent;
  }
  .actions-paragraphe {
    display: inline-flex;
    gap: 0.5rem;
    margin-left: 0.6rem;
  }
  .lien-action {
    font: inherit;
    font-size: 0.8rem;
    padding: 0.15rem 0.45rem;
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    background: var(--fond-surface);
    color: var(--corr-style-texte);
    cursor: pointer;
  }
  .lien-action:hover {
    background: var(--corr-style-fond);
  }
  .aucune-correction {
    color: var(--encre-douce);
    font-style: italic;
  }
</style>