<script lang="ts">
  import Carte from '../lib/composants/Carte.svelte';
  import EtatVide from '../lib/composants/EtatVide.svelte';
</script>

<section class="accueil">
  <h1>Bienvenue dans votre atelier de correction</h1>
  <p class="accueil__intro">
    Relisez votre manuscrit en douceur : chaque texte soumis est analysé puis
    présenté dans un atelier de relecture, corrections en couleur et à votre main.
  </p>

  <Carte titre="Vos manuscrits">
    <EtatVide
      titre="Aucun manuscrit pour le moment"
      message="La création de votre premier projet sera disponible très prochainement ici."
    />
  </Carte>
</section>

<style>
  .accueil {
    display: grid;
    gap: 1.25rem;
  }
  .accueil h1 {
    margin: 0;
    font-size: 1.6rem;
  }
  .accueil__intro {
    margin: 0;
    max-width: 60ch;
    color: var(--encre-douce);
  }
</style>