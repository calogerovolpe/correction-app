<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    titre?: string;
    surtitre?: string;
    children: Snippet;
  }

  let { titre, surtitre, children }: Props = $props();
</script>

<section class="carte">
  {#if surtitre}
    <p class="carte__surtitre">{surtitre}</p>
  {/if}
  {#if titre}
    <h2 class="carte__titre">{titre}</h2>
  {/if}
  <div class="carte__contenu">
    {@render children()}
  </div>
</section>

<style>
  .carte {
    background: var(--fond-surface);
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    padding: 1.25rem;
  }
  .carte__surtitre {
    margin: 0 0 0.25rem;
    font-size: 0.85rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--encre-douce);
  }
  .carte__titre {
    margin: 0 0 0.75rem;
    font-size: 1.15rem;
  }
</style>