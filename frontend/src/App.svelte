<script lang="ts">
  import NavBar from './lib/composants/NavBar.svelte';
  import Accueil from './routes/Accueil.svelte';
  import { routeCourante } from './lib/router';
</script>

<div class="enveloppe">
  <NavBar />
  <main>
    {#if $routeCourante === '/'}
      <Accueil />
    {:else}
      <section class="introuvable" aria-labelledby="titre-404">
        <h1 id="titre-404">Page introuvable</h1>
        <p>
          Cette page n'existe pas encore.
          <a href="#/">Revenir à l'accueil</a>.
        </p>
      </section>
    {/if}
  </main>
  <footer class="pied">
    <p>Correction de manuscrit — application locale, vos textes restent sur votre machine.</p>
  </footer>
</div>