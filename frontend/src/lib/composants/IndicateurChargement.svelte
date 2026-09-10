<script lang="ts">
  interface Props {
    message: string;
  }

  let { message }: Props = $props();
</script>

<!-- Indicateur d'attente unifié (jalon F4) : spinner CSS local-first (aucune
     ressource distante), annoncé aux lecteurs d'écran via role="status". -->
<p class="indicateur" role="status">
  <span class="indicateur__spinner" aria-hidden="true"></span>
  <span>{message}</span>
</p>

<style>
  .indicateur {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 0.5rem 0;
    color: var(--encre-douce);
    font-style: italic;
  }
  .indicateur__spinner {
    flex: 0 0 auto;
    width: 1rem;
    height: 1rem;
    border-radius: 50%;
    border: 2px solid var(--accent-doux);
    border-top-color: var(--accent);
    animation: indicateur-rotation 0.9s linear infinite;
  }
  @keyframes indicateur-rotation {
    to {
      transform: rotate(360deg);
    }
  }
  /* Mouvement réduit : la rotation ralentit au lieu de disparaître, l'attente
     reste lisible sans gêner les personnes sensibles au mouvement. */
  @media (prefers-reduced-motion: reduce) {
    .indicateur__spinner {
      animation-duration: 3s;
    }
  }
</style>