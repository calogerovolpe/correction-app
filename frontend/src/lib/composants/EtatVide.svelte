<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    titre: string;
    message?: string;
    /** Micro-illustration décorative (glyphe sobre, aria-hidden) : elle
     *  humanise l'état vide sans jamais être lue par les lecteurs d'écran. */
    illustration?: string;
    action?: Snippet;
  }

  let { titre, message, illustration = '✒️', action }: Props = $props();
</script>

<div class="etat-vide" role="status">
  <span class="etat-vide__illustration" aria-hidden="true">{illustration}</span>
  <h3 class="etat-vide__titre">{titre}</h3>
  {#if message}
    <p class="etat-vide__message">{message}</p>
  {/if}
  {#if action}
    <div class="etat-vide__action">{@render action()}</div>
  {/if}
</div>

<style>
  .etat-vide {
    padding: 2rem 1.5rem;
    text-align: center;
    background: var(--fond-surface);
    border: 1px dashed var(--bordure);
    border-radius: var(--rayon);
  }
  .etat-vide__illustration {
    display: block;
    margin-bottom: 0.5rem;
    font-size: 1.6rem;
    line-height: 1;
  }
  .etat-vide__titre {
    margin: 0 0 0.5rem;
    font-size: 1.05rem;
  }
  .etat-vide__message {
    margin: 0 auto;
    color: var(--encre-douce);
    max-width: 48ch;
  }
  .etat-vide__action {
    margin-top: 1rem;
  }
</style>