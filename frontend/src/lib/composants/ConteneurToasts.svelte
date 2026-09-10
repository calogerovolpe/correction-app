<script lang="ts">
  import { fermerToast, toasts, type Toast } from '../toasts';

  /** Conteneur unique des notifications toast (jalon F4), monté UNE fois
   *  dans `App.svelte` : deux zones live distinctes — polie pour les
   *  succès/infos (`role="status"`, `aria-live="polite"`), assertive pour
   *  les erreurs bloquantes (`role="alert"`, `aria-live="assertive"`).
   *  Chaque toast offre un bouton de fermeture accessible (Espace/Entrée),
   *  en complément de l'auto-fermeture minutée. */

  const polis = $derived($toasts.filter((t) => t.type !== 'erreur'));
  const assertifs = $derived($toasts.filter((t) => t.type === 'erreur'));
</script>

<div class="conteneur-toasts">
  {#each [polis, assertifs] as file, index (index)}
    <div
      class="toasts-zone"
      role={index === 0 ? 'status' : 'alert'}
      aria-live={index === 0 ? 'polite' : 'assertive'}
      aria-atomic="false"
    >
      {#each file as t (t.id)}
        <div class="toast toast--{t.type}">
          <p class="toast__message">{t.message}</p>
          <button
            type="button"
            class="toast__fermer"
            aria-label="Fermer la notification"
            onclick={() => fermerToast(t.id)}
          >
            ×
          </button>
        </div>
      {/each}
    </div>
  {/each}
</div>

<style>
  .conteneur-toasts {
    position: fixed;
    right: 1rem;
    bottom: 1rem;
    z-index: 400;
    display: grid;
    gap: 0.5rem;
    justify-items: end;
    pointer-events: none;
    max-width: calc(100vw - 2rem);
  }
  .toasts-zone {
    display: grid;
    gap: 0.5rem;
    justify-items: end;
  }
  .toast {
    pointer-events: auto;
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
    max-width: 22rem;
    padding: 0.65rem 0.8rem;
    border-radius: var(--rayon);
    box-shadow: 0 6px 18px rgba(42, 38, 34, 0.22);
    font-size: 0.95rem;
    line-height: 1.4;
  }
  .toast__message {
    margin: 0;
  }
  .toast__fermer {
    font: inherit;
    font-size: 1.05rem;
    line-height: 1;
    padding: 0 0.2rem;
    margin: -0.1rem -0.1rem 0 0;
    background: transparent;
    border: none;
    border-radius: 3px;
    cursor: pointer;
    color: inherit;
  }
  /* Succès : vert AA — #fffdf8 sur #3e6b4f ≈ 5.6:1. */
  .toast--succes {
    background: var(--succes);
    color: #fffdf8;
  }
  /* Info : surface claire, encre AA sur fond clair. */
  .toast--info {
    background: var(--fond-surface);
    color: var(--encre);
    border: 1px solid var(--bordure);
  }
  /* Erreur : rouge AA — #fffdf8 sur #b3402a ≈ 4.7:1. */
  .toast--erreur {
    background: var(--erreur);
    color: #fffdf8;
  }
  @media (prefers-reduced-motion: reduce) {
    .toast {
      transition: none;
    }
  }
</style>