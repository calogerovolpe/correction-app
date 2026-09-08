<script lang="ts">
  import type { Snippet } from 'svelte';

  /** Bandeau de message (F2) : erreur (refus explicites) ou avertissement,
   *  annoncé aux lecteurs d'écran via `role="alert"`. */

  interface Props {
    variante?: 'erreur' | 'avertissement' | 'succes';
    children: Snippet;
  }

  let { variante = 'avertissement', children }: Props = $props();
</script>

<div class="bandeau bandeau--{variante}" role="alert">
  {@render children()}
</div>

<style>
  .bandeau {
    margin: 0;
    padding: 0.6rem 0.85rem;
    border-radius: var(--rayon);
    font-size: 0.95rem;
    line-height: 1.4;
  }
  .bandeau--erreur {
    color: var(--erreur);
    background: var(--corr-forme-fond);
    border: 1px solid var(--erreur);
  }
  .bandeau--avertissement {
    color: var(--attention);
    background: #fff8e1;
    border: 1px solid var(--attention);
  }
  .bandeau--succes {
    color: var(--succes);
    background: var(--corr-embellissement-fond);
    border: 1px solid var(--succes);
  }
</style>