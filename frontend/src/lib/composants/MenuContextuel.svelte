<script lang="ts">
  /** Menu contextuel RICHE (jalon A / F3, décision 36) : ouvert au clic droit
   *  sur une marque OU une sélection. Position `fixed` recentrée dans la
   *  fenêtre (robuste au scroll). Fermeture à Échap / clic extérieur prise en
   *  charge par l'atelier (listener application + action). */

  export interface ElementMenu {
    cle: string;
    libelle: string;
  }

  interface Props {
    x: number;
    y: number;
    items: ElementMenu[];
    onChoisir: (cle: string) => void;
  }

  let { x, y, items, onChoisir }: Props = $props();

  /** Action Svelte : positionne au curseur puis recentre si le menu sort de
   *  l'écran (avant : hors écran près des bords — piège du jalon A). */
  function positionner(element: HTMLElement): { destroy: () => void } {
    const r = element.getBoundingClientRect();
    element.style.left =
      x + r.width > window.innerWidth - 8
        ? `${Math.max(8, x - r.width)}px`
        : `${x}px`;
    element.style.top =
      y + r.height > window.innerHeight - 8
        ? `${Math.max(8, y - r.height)}px`
        : `${y}px`;
    return { destroy: () => undefined };
  }
</script>

<div class="menu-contextuel" role="menu" aria-label="Actions de correction" use:positionner>
  {#each items as item (item.cle)}
    <button type="button" role="menuitem" class="item-menu" onclick={() => onChoisir(item.cle)}>
      {item.libelle}
    </button>
  {/each}
</div>

<style>
  .menu-contextuel {
    position: fixed;
    z-index: 300;
    min-width: 240px;
    background: var(--fond-surface);
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    padding: 0.25rem 0;
  }
  .item-menu {
    text-align: left;
    font: inherit;
    font-size: 0.9rem;
    padding: 0.5rem 0.9rem;
    border: none;
    background: transparent;
    color: var(--encre);
    cursor: pointer;
  }
  .item-menu:hover {
    background: var(--corr-style-fond);
  }
</style>