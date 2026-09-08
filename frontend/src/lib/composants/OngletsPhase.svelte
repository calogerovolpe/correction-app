<script lang="ts">
  import type { OngletAtelier } from '../api/types';

  /** Barre d'onglets hybrides (jalon R1-a / F3) : « Tout » = superposition,
   *  un onglet par phase = projection (filtre côté serveur, zéro API LLM
   *  ajoutée). Le compteur de chaque phase part de `compteurs` (état complet). */

  interface Props {
    onglet: OngletAtelier;
    compteurs: Record<string, number>;
    aEmbellissement: boolean;
    onChangerOnglet: (onglet: OngletAtelier) => void;
  }

  let { onglet, compteurs, aEmbellissement, onChangerOnglet }: Props = $props();

  const ONGLETS: { valeur: OngletAtelier; libelle: string }[] = [
    { valeur: 'forme', libelle: 'Forme' },
    { valeur: 'style', libelle: 'Style' },
    { valeur: 'technique', libelle: 'Technique' },
  ];

  function totalToutesPhases(): number {
    return (
      (compteurs['forme'] ?? 0) +
      (compteurs['style'] ?? 0) +
      (compteurs['technique'] ?? 0) +
      (compteurs['embellissement'] ?? 0)
    );
  }
</script>

<div class="onglets" role="tablist" aria-label="Phases de correction">
  <button
    type="button"
    role="tab"
    class="onglet onglet--tout"
    aria-selected={onglet === 'tout'}
    onclick={() => onChangerOnglet('tout')}
  >
    Tout <span class="onglet__compteur">{totalToutesPhases()}</span>
  </button>
  {#each ONGLETS as phase (phase.valeur)}
    <button
      type="button"
      role="tab"
      class="onglet onglet--{phase.valeur}"
      aria-selected={onglet === phase.valeur}
      onclick={() => onChangerOnglet(phase.valeur)}
    >
      {phase.libelle}
      {#if (compteurs[phase.valeur] ?? 0) > 0}
        <span class="onglet__compteur">{compteurs[phase.valeur]}</span>
      {/if}
    </button>
  {/each}
  {#if aEmbellissement || (compteurs['embellissement'] ?? 0) > 0}
    <button
      type="button"
      role="tab"
      class="onglet onglet--embellissement"
      aria-selected={onglet === 'embellissement'}
      onclick={() => onChangerOnglet('embellissement')}
    >
      Embellissement
      {#if (compteurs['embellissement'] ?? 0) > 0}
        <span class="onglet__compteur">{compteurs['embellissement']}</span>
      {/if}
    </button>
  {/if}
</div>

<style>
  .onglets {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0 0 0.75rem;
  }
  .onglet {
    font: inherit;
    font-size: 0.9rem;
    line-height: 1.2;
    padding: 0.35rem 0.8rem;
    border: 1px solid var(--bordure);
    border-radius: 999px;
    background: var(--fond-surface);
    color: var(--encre);
    cursor: pointer;
    transition:
      background-color 0.15s ease,
      border-color 0.15s ease;
  }
  .onglet:hover {
    border-color: var(--accent);
    background: var(--accent-doux);
  }
  .onglet[aria-selected='true'] {
    font-weight: 700;
    border-color: var(--accent);
    background: var(--accent);
    color: #fffdf8;
  }
  .onglet__compteur {
    display: inline-block;
    margin-left: 0.35rem;
    padding: 0 0.4rem;
    border-radius: 999px;
    background: rgba(0, 0, 0, 0.08);
    font-size: 0.75rem;
    line-height: 1.3;
  }
  .onglet[aria-selected='true'] .onglet__compteur {
    background: rgba(255, 255, 255, 0.2);
  }
</style>