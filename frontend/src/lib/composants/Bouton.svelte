<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    variante?: 'primaire' | 'secondaire' | 'danger';
    type?: 'button' | 'submit';
    desactive?: boolean;
    title?: string;
    onclick?: (evenement: MouseEvent) => void;
    children: Snippet;
  }

  let {
    variante = 'primaire',
    type = 'button',
    desactive = false,
    title = undefined,
    onclick = undefined,
    children,
  }: Props = $props();
</script>

<button class="bouton bouton--{variante}" {type} disabled={desactive} {title} {onclick}>
  {@render children()}
</button>

<style>
  .bouton {
    font: inherit;
    font-size: 0.95rem;
    line-height: 1.2;
    padding: 0.5rem 1rem;
    border-radius: var(--rayon);
    border: 1px solid var(--bordure);
    cursor: pointer;
    transition:
      background-color 0.15s ease,
      border-color 0.15s ease;
  }
  .bouton:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .bouton--primaire {
    background: var(--accent);
    border-color: var(--accent);
    color: #fffdf8;
  }
  .bouton--primaire:hover:not(:disabled) {
    background: var(--accent-fonce);
    border-color: var(--accent-fonce);
  }
  .bouton--secondaire {
    background: transparent;
    color: var(--encre);
  }
  .bouton--secondaire:hover:not(:disabled) {
    background: var(--accent-doux);
    border-color: var(--accent);
  }
  .bouton--danger {
    background: transparent;
    color: var(--erreur);
    border-color: var(--erreur);
  }
  .bouton--danger:hover:not(:disabled) {
    background: var(--erreur);
    color: #fffdf8;
  }
</style>