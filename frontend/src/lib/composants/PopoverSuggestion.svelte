<script lang="ts">
  import Bouton from './Bouton.svelte';

  /** Popover de suggestion (embellissement / alternatives, jalon A / F3) :
   *  proposition du LLM affichée près du curseur, l'auteur APPLIQUE ou ANNULE
   *  (aucune modification en arrière-plan avant validation). */

  interface Props {
    type: 'embellissement' | 'alternatives';
    texte?: string;
    explication?: string;
    alternatives?: string[];
    erreur?: string;
    onAppliquer: (texte: string) => void;
    onAnnuler: () => void;
  }

  let { type, texte, explication, alternatives, erreur, onAppliquer, onAnnuler }: Props = $props();

  function positionner(element: HTMLElement): { destroy: () => void } {
    const r = element.getBoundingClientRect();
    const x = Math.max(
      8,
      Math.min(
        window.innerWidth - r.width - 8,
        window.innerWidth / 2 - r.width / 2,
      ),
    );
    const y = Math.max(
      8,
      Math.min(
        window.innerHeight - r.height - 8,
        window.innerHeight / 2 - r.height / 2,
      ),
    );
    element.style.left = `${x}px`;
    element.style.top = `${y}px`;
    return { destroy: () => undefined };
  }
</script>

<div class="popover" role="dialog" aria-label="Proposition de l'IA" use:positionner>
  {#if erreur}
    <p class="popover__erreur">{erreur}</p>
    <Bouton variante="secondaire" onclick={() => onAnnuler()}>Fermer</Bouton>
  {:else if type === 'embellissement' && texte}
    <h3 class="popover__titre">Embellissement proposé</h3>
    <p class="popover__proposition">{texte}</p>
    {#if explication}
      <p class="popover__explication">{explication}</p>
    {/if}
    <div class="popover__actions">
      <Bouton variante="primaire" onclick={() => onAppliquer(texte)}>Appliquer</Bouton>
      <Bouton variante="secondaire" onclick={() => onAnnuler()}>Annuler</Bouton>
    </div>
  {:else if type === 'alternatives' && alternatives && alternatives.length > 0}
    <h3 class="popover__titre">Alternatives proposées</h3>
    {#if explication}
      <p class="popover__explication">{explication}</p>
    {/if}
    <ul class="popover__liste">
      {#each alternatives as alternative (alternative)}
        <li>
          <button
            type="button"
            class="popover__choix"
            onclick={() => onAppliquer(alternative)}
          >
            {alternative}
          </button>
        </li>
      {/each}
    </ul>
    <div class="popover__actions">
      <Bouton variante="secondaire" onclick={() => onAnnuler()}>Annuler</Bouton>
    </div>
  {:else}
    <p class="popover__erreur">Aucune proposition reçue.</p>
    <Bouton variante="secondaire" onclick={() => onAnnuler()}>Fermer</Bouton>
  {/if}
</div>

<style>
  .popover {
    position: fixed;
    z-index: 250;
    width: 340px;
    max-width: calc(100vw - 2rem);
    background: var(--fond-surface);
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
    padding: 1rem;
  }
  .popover__titre {
    margin: 0 0 0.4rem;
    font-size: 1rem;
  }
  .popover__proposition {
    margin: 0 0 0.5rem;
    background: var(--corr-embellissement-fond);
    border-radius: var(--rayon);
    padding: 0.5rem;
    white-space: pre-wrap;
  }
  .popover__explication {
    margin: 0 0 0.5rem;
    color: var(--encre-douce);
    font-size: 0.9rem;
  }
  .popover__liste {
    list-style: none;
    margin: 0 0 0.5rem;
    padding: 0;
    display: grid;
    gap: 0.35rem;
  }
  .popover__choix {
    width: 100%;
    text-align: left;
    font: inherit;
    padding: 0.4rem 0.6rem;
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    background: var(--fond-page);
    color: var(--encre);
    cursor: pointer;
  }
  .popover__choix:hover {
    background: var(--corr-style-fond);
    border-color: var(--corr-style-texte);
  }
  .popover__actions {
    display: flex;
    gap: 0.6rem;
    justify-content: flex-end;
  }
  .popover__erreur {
    color: var(--erreur);
    margin: 0 0 0.5rem;
  }
</style>