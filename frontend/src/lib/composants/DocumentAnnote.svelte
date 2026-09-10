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
    /** FA7 — groupe de la correction active (mise en évidence des marques). */
    groupeActif: string | null;
    /** FA7 — info-bulle contextuelle : signale une marque (survol ou focus
     *  clavier) avec l'élément lui-même pour positionner la bulle. */
    onSignalerMarque: (groupe: string, element: HTMLElement) => void;
    onQuitterMarque: () => void;
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
    groupeActif,
    onSignalerMarque,
    onQuitterMarque,
  }: Props = $props();

  /** Navigation clavier ←/→ entre les marques INTERACTIVES (boutons
   *  [data-groupe]) VISIBLES. FA4 : les <del> (non focusables, sans action)
   *  sont exclus du parcours fléché — la chaîne de focus reste fluide. */
  function naviguerClavier(evenement: KeyboardEvent): void {
    if (evenement.key !== 'ArrowRight' && evenement.key !== 'ArrowLeft') return;
    const conteneur = document.getElementById('document-annote');
    if (!conteneur) return;
    const cibles = Array.from(
      conteneur.querySelectorAll<HTMLElement>('button[data-groupe]'),
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
    <del class="del {s.classes}" data-groupe={s.groupe}>
      {@render contenuEnrichi(s.del, s.gras, s.italique, s.souligne)}
    </del>
    <button
      type="button"
      class="ins ins--forme {s.classes}"
      class:marque-active={s.groupe === groupeActif}
      data-groupe={s.groupe}
      onclick={() => onSelectionnerGroupe(s.groupe)}
      onmouseenter={(e) => onSignalerMarque(s.groupe, e.currentTarget)}
      onmouseleave={() => onQuitterMarque()}
      onfocus={(e) => onSignalerMarque(s.groupe, e.currentTarget)}
      onblur={() => onQuitterMarque()}
    >
      {@render contenuEnrichi(s.ins, s.gras, s.italique, s.souligne)}
    </button>
  {:else if segmentTexte(s).groupe}
    <button
      type="button"
      class="seg-texte {segmentTexte(s).classes}"
      class:marque-active={segmentTexte(s).groupe === groupeActif}
      data-groupe={segmentTexte(s).groupe}
      onclick={() => onSelectionnerGroupe(segmentTexte(s).groupe!)}
      onmouseenter={(e) => onSignalerMarque(segmentTexte(s).groupe!, e.currentTarget)}
      onmouseleave={() => onQuitterMarque()}
      onfocus={(e) => onSignalerMarque(segmentTexte(s).groupe!, e.currentTarget)}
      onblur={() => onQuitterMarque()}
    >
      {@render contenuEnrichi(
        segmentTexte(s).texte,
        segmentTexte(s).gras,
        segmentTexte(s).italique,
        segmentTexte(s).souligne,
      )}
    </button>
  {:else}
    <span class="seg-texte {segmentTexte(s).classes}">
      {@render contenuEnrichi(
        segmentTexte(s).texte,
        segmentTexte(s).gras,
        segmentTexte(s).italique,
        segmentTexte(s).souligne,
      )}
    </span>
  {/if}
{/snippet}

<!-- FA4 — fidélité du formatage Word : le gras, l'italique et le souligné de
     l'auteur (attributs `gras` / `italique` / `souligne` transmis par le rendu)
     sont restitués en balisage SÉMANTIQUE <strong> / <em> / <u> (combinaisons
     emboîtées). Le texte reste échappé par le binding Svelte ({texte}). -->
{#snippet contenuEnrichi(
    texte: string,
    gras: boolean,
    italique: boolean,
    souligne: boolean,
  )}
  {#if gras}
    {#if italique}
      {#if souligne}<strong><em><u>{texte}</u></em></strong>
      {:else}<strong><em>{texte}</em></strong>{/if}
    {:else if souligne}
      <strong><u>{texte}</u></strong>
    {:else}
      <strong>{texte}</strong>
    {/if}
  {:else if italique}
    {#if souligne}<em><u>{texte}</u></em>
    {:else}<em>{texte}</em>{/if}
  {:else if souligne}
    <u>{texte}</u>
  {:else}
    {texte}
  {/if}
{/snippet}

<style>
  /* FA4 — le reset « color: inherit; background: transparent » qui écrasait
     les couleurs réelles des couches (spécificité scoped > classes globales)
     a été RETIRÉ : le reset neutre des marques-boutons vit désormais dans
     atelier.css en spécificité ZÉRO (`:where(button.ins, button.seg-texte)`),
     laissant `.ins--forme`, `.mark-technique`, `.mark-style`, `.refusee`… 
     maîtres des couleurs du design system. */
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