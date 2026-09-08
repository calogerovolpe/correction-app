<script lang="ts">
  /** Toggle « Masquer les paragraphes sans correction » (décision 35, E5) :
   *  le texte ENTIER est affiché par défaut (décoché) ; le masquage est au
   *  choix de l'auteur. État local à l'atelier. */

  interface Props {
    masque: boolean;
    nbMasques: number;
    onchange: (masque: boolean) => void;
  }

  let { masque, nbMasques, onchange }: Props = $props();
</script>

<label class="toggle-masquer">
  <input
    type="checkbox"
    checked={masque}
    onchange={(e) => onchange(e.currentTarget.checked)}
  />
  <span>
    Masquer les paragraphes sans correction
    {#if nbMasques > 0}
      <span class="toggle-masquer__compteur">({nbMasques} masqué{nbMasques > 1 ? 's' : ''})</span>
    {/if}
  </span>
</label>

<style>
  .toggle-masquer {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
    cursor: pointer;
    user-select: none;
  }
  .toggle-masquer input {
    width: 1.05rem;
    height: 1.05rem;
    accent-color: var(--accent);
    cursor: pointer;
  }
  .toggle-masquer__compteur {
    color: var(--encre-douce);
    font-size: 0.85rem;
  }
</style>