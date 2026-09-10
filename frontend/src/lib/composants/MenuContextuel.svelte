<script lang="ts">
  /** Menu contextuel RICHE (jalon A / F3, décision 36) : ouvert au clic droit
   *  sur une marque OU une sélection. Position `fixed` recentrée dans la
   *  fenêtre (robuste au scroll). FA7 — accessibilité complète : focus initial
   *  sur le premier élément, navigation ↑/↓/Début/Fin, fermeture par Tab avec
   *  RESTAURATION du focus sur l'élément déclencheur (piège de focus évité ;
   *  Échap et le clic extérieur sont gérés par l'atelier). */

  export interface ElementMenu {
    cle: string;
    libelle: string;
  }

  interface Props {
    x: number;
    y: number;
    items: ElementMenu[];
    onChoisir: (cle: string) => void;
    /** FA7 — élément qui a ouvert le menu (marque, texte…) : le focus lui est
     *  rendu à la fermeture. */
    declencheur?: HTMLElement | null;
    /** FA7 — fermeture demandée par le menu (touche Tab). */
    onFermer: () => void;
  }

  let { x, y, items, onChoisir, declencheur = null, onFermer }: Props = $props();

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

  /** FA7 — focus initial sur le premier élément du menu ; à la fermeture
   *  (démontage), le focus est rendu au déclencheur (restauration). */
  function gererFocus(element: HTMLElement): { destroy: () => void } {
    const premier = element.querySelector<HTMLElement>('[role="menuitem"]');
    (premier ?? element).focus();
    return {
      destroy: () => {
        if (declencheur?.isConnected) declencheur.focus();
      },
    };
  }

  /** FA7 — navigation clavier dans le menu (pattern WAI-ARIA). */
  function naviguer(evenement: KeyboardEvent): void {
    const conteneur = evenement.currentTarget as HTMLElement;
    const elements = Array.from(
      conteneur.querySelectorAll<HTMLElement>('[role="menuitem"]'),
    );
    if (elements.length === 0) return;
    const actif = document.activeElement as HTMLElement | null;
    const index = actif ? elements.indexOf(actif) : -1;
    if (evenement.key === 'ArrowDown' || evenement.key === 'ArrowUp') {
      evenement.preventDefault();
      const pas = evenement.key === 'ArrowDown' ? 1 : -1;
      const nouveau =
        index === -1
          ? pas === 1
            ? 0
            : elements.length - 1
          : (index + pas + elements.length) % elements.length;
      elements[nouveau].focus();
    } else if (evenement.key === 'Home' || evenement.key === 'End') {
      evenement.preventDefault();
      const nouveau =
        evenement.key === 'Home' ? 0 : elements.length - 1;
      elements[nouveau].focus();
    } else if (evenement.key === 'Tab') {
      // Le focus quitte le menu : fermer (et rendre le focus au déclencheur).
      evenement.preventDefault();
      onFermer();
    }
  }
</script>

<div
  class="menu-contextuel"
  role="menu"
  aria-label="Actions de correction"
  tabindex="-1"
  use:positionner
  use:gererFocus
  onkeydown={naviguer}
>
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