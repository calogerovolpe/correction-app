<script lang="ts">
  import { onMount } from 'svelte';
  import Bouton from './Bouton.svelte';

  interface Props {
    titre: string;
    message?: string;
    annuler?: string;
    confirmer?: string;
    onFermer?: () => void;
    onConfirmer?: () => void;
  }

  let {
    titre,
    message = '',
    annuler = 'Annuler',
    confirmer = 'Confirmer',
    onFermer = undefined,
    onConfirmer = undefined,
  }: Props = $props();

  let dialogue: HTMLDivElement | undefined = $state();

  onMount(() => {
    dialogue?.focus();
  });

  function gererTouche(evenement: KeyboardEvent): void {
    if (evenement.key === 'Escape') onFermer?.();
  }
</script>

<div class="modale-fond" role="presentation" onkeydown={gererTouche}>
  <div
    class="modale"
    role="dialog"
    aria-modal="true"
    aria-labelledby="modale-titre"
    tabindex="-1"
    bind:this={dialogue}
  >
    <h2 class="modale__titre" id="modale-titre">{titre}</h2>
    {#if message}
      <p class="modale__message">{message}</p>
    {/if}
    <div class="modale__actions">
      <Bouton variante="secondaire" onclick={onFermer}>{annuler}</Bouton>
      <Bouton variante="danger" onclick={onConfirmer}>{confirmer}</Bouton>
    </div>
  </div>
</div>

<style>
  .modale-fond {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(42, 38, 34, 0.45);
    padding: 1rem;
  }
  .modale {
    max-width: 28rem;
    width: 100%;
    background: var(--fond-surface);
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    padding: 1.5rem;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  }
  .modale__titre {
    margin: 0 0 0.75rem;
    font-size: 1.15rem;
  }
  .modale__message {
    margin: 0 0 1.25rem;
    color: var(--encre-douce);
  }
  .modale__actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
  }
</style>