<script lang="ts">
  import { routeCourante } from '../router';
  import type { Snippet } from 'svelte';

  interface Props {
    liens?: { chemin: string; libelle: string }[];
    children?: Snippet;
  }

  let { liens = [{ chemin: '/', libelle: 'Accueil' }], children }: Props = $props();
</script>

<header class="navbar">
  <a class="navbar__marque" href="#/" aria-label="Accueil de l'application">
    <span class="navbar__titre">Correction de manuscrit</span>
    <span class="navbar__sous-titre">Atelier de relecture</span>
  </a>
  <nav aria-label="Navigation principale">
    <ul class="navbar__liens">
      <li>
        {#each liens as lien (lien.chemin)}
          <a
            href="#{lien.chemin}"
            class="navbar__lien"
            aria-current={$routeCourante === lien.chemin ? 'page' : undefined}
          >
            {lien.libelle}
          </a>
        {/each}
      </li>
      {#if children}
        {@render children()}
      {/if}
    </ul>
  </nav>
</header>

<style>
  .navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--bordure);
  }
  .navbar__marque {
    display: flex;
    flex-direction: column;
    text-decoration: none;
    line-height: 1.2;
  }
  .navbar__titre {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--encre);
  }
  .navbar__sous-titre {
    font-size: 0.8rem;
    color: var(--encre-douce);
  }
  .navbar__liens {
    list-style: none;
    display: flex;
    gap: 1rem;
    margin: 0;
    padding: 0;
    align-items: center;
  }
  .navbar__lien {
    padding: 0.35rem 0.6rem;
    border-radius: var(--rayon);
    color: var(--encre);
    text-decoration: none;
  }
  .navbar__lien:hover {
    background: var(--accent-doux);
  }
  .navbar__lien[aria-current='page'] {
    background: var(--accent-doux);
    color: var(--accent-fonce);
    font-weight: 600;
  }
</style>