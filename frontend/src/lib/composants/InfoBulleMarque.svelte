<script lang="ts">
  import type { CorrectionBarre } from '../api/types';
  import { premierePhrase } from '../pedagogie';

  /** FA7 — info-bulle contextuelle (popover de résumé) : s'affiche près d'une
   *  marque du manuscrit au SURVOL ou au FOCUS (clavier) pour lire un résumé
   *  de la correction sans quitter le texte des yeux. Fermeture : Échap (géré
   *  par l'atelier), sortie de la marque (mouseleave/blur), clic ailleurs ou
   *  clic sur une autre marque. Repositionnée au défilement pour rester
   *  collée à son ancre (défilement fluide, onglets, fenêtre redimensionnée). */

  interface Props {
    correction: CorrectionBarre;
    ancre: HTMLElement | null;
  }

  let { correction, ancre }: Props = $props();

  /** Première phrase de l'explication (résumé rapide, pas la trame complète). */
  const resume = $derived(premierePhrase(correction.explication));

  /** Action Svelte : place la bulle près de l'ancre (au-dessus si possible,
   *  sinon en dessous), recentrée dans la fenêtre ; repositionnée à chaque
   *  défilement/resize tant qu'elle est montée. */
  function positionner(element: HTMLElement): { destroy: () => void } {
    const placer = (): void => {
      if (!ancre || !ancre.isConnected) return;
      const rect = ancre.getBoundingClientRect();
      const largeur = element.offsetWidth || 300;
      const hauteur = element.offsetHeight || 80;
      const x = Math.max(
        8,
        Math.min(
          window.innerWidth - largeur - 8,
          rect.left + rect.width / 2 - largeur / 2,
        ),
      );
      const y =
        rect.top - hauteur - 10 >= 8 ? rect.top - hauteur - 10 : rect.bottom + 10;
      element.style.left = `${x}px`;
      element.style.top = `${y}px`;
    };
    placer();
    window.addEventListener('scroll', placer, true);
    window.addEventListener('resize', placer);
    return {
      destroy: () => {
        window.removeEventListener('scroll', placer, true);
        window.removeEventListener('resize', placer);
      },
    };
  }
</script>

<div class="infobulle" id="infobulle-marque" role="tooltip" use:positionner>
  <p class="infobulle__titre">
    {correction.titre || correction.type.replace('_', ' ')}
  </p>
  {#if correction.regle}
    <p class="infobulle__regle">
      <span class="badge-regle">Règle</span>
      {correction.regle}
    </p>
  {/if}
  {#if correction.correction && correction.correction !== correction.original}
    <p class="infobulle__diff">
      <span class="infobulle__origine">« {correction.original} »</span>
      <span aria-hidden="true"> → </span>
      <span class="infobulle__proposition">« {correction.correction} »</span>
    </p>
  {/if}
  <p class="infobulle__resume">{resume}</p>
</div>

<style>
  .infobulle {
    position: fixed;
    z-index: 260;
    width: 320px;
    max-width: calc(100vw - 2rem);
    background: var(--fond-surface);
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
    padding: 0.7rem 0.85rem;
    display: grid;
    gap: 0.3rem;
    pointer-events: none;
  }
  .infobulle__titre {
    margin: 0;
    font-size: 0.92rem;
    font-weight: 700;
  }
  .infobulle__regle {
    margin: 0;
    font-size: 0.82rem;
  }
  .infobulle__diff {
    margin: 0;
    font-size: 0.85rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.15rem;
    align-items: baseline;
  }
  .infobulle__origine {
    text-decoration: line-through;
    color: var(--corr-forme-texte);
    background: var(--corr-forme-fond);
    border-radius: 3px;
    padding: 0 0.25rem;
  }
  .infobulle__proposition {
    color: var(--succes);
    background: var(--corr-embellissement-fond);
    border-radius: 3px;
    padding: 0 0.25rem;
    font-weight: 600;
  }
  .infobulle__resume {
    margin: 0;
    color: var(--encre-douce);
    font-size: 0.82rem;
    line-height: 1.45;
  }
</style>