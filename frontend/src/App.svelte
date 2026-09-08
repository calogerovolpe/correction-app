<script lang="ts">
  import NavBar from './lib/composants/NavBar.svelte';
  import Accueil from './routes/Accueil.svelte';
  import Atelier from './routes/Atelier.svelte';
  import Soumission from './routes/Soumission.svelte';
  import Suivi from './routes/Suivi.svelte';
  import { routeCourante } from './lib/router';

  /** Extraît l'identifiant de suivi d'une route hash `#/analyses/{id}`. */
  function idSuivi(chemin: string): number | null {
    const prefixe = '/analyses/';
    if (!chemin.startsWith(prefixe)) return null;
    const reste = chemin.slice(prefixe.length);
    if (!/^\d+$/.test(reste)) return null;
    return Number(reste);
  }

  /** Extraît l'identifiant d'atelier d'une route hash `#/atelier/{id}`. */
  function idAtelier(chemin: string): number | null {
    const prefixe = '/atelier/';
    if (!chemin.startsWith(prefixe)) return null;
    const reste = chemin.slice(prefixe.length);
    if (!/^\d+$/.test(reste)) return null;
    return Number(reste);
  }
</script>

<div class="enveloppe">
  <NavBar />
  <main>
    {#if $routeCourante === '/'}
      <Accueil />
    {:else if $routeCourante === '/soumission'}
      <Soumission />
    {:else if idAtelier($routeCourante) !== null}
      <Atelier analyseId={idAtelier($routeCourante)!} />
    {:else if idSuivi($routeCourante) !== null}
      <Suivi analyseId={idSuivi($routeCourante)!} />
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