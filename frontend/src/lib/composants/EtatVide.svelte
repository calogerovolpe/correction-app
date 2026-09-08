<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    titre: string;
    message?: string;
    action?: Snippet;
  }

  let { titre, message, action }: Props = $props();
</script>

<div class="etat-vide" role="status">
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
    padding: 2rem;
    text-align: center;
    background: var(--fond-surface);
    border: 1px dashed var(--bordure);
    border-radius: var(--rayon);
  }
  .etat-vide__titre {
    margin: 0 0 0.5rem;
    font-size: 1.05rem;
  }
  .etat-vide__message {
    margin: 0;
    color: var(--encre-douce);
  }
  .etat-vide__action {
    margin-top: 1rem;
  }
</style>