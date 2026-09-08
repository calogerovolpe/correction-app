<script lang="ts">
  import type { CorrectionBarre } from '../api/types';

  /** Barre latérale de l'atelier (F3) : liste des corrections (lecture seule
   *  selon la décision 36 — les choix se font dans le menu ou par clic sur la
   *  marque) + détail de la correction active + section « Incohérences
   *  Techniques » (même lecture de couple que le rendu). */

  interface Props {
    corrections: CorrectionBarre[];
    active: CorrectionBarre | null;
    onSelectionnerGroupe: (groupe: string) => void;
  }

  let { corrections, active, onSelectionnerGroupe }: Props = $props();

  const LIBELLES_PHASES: Record<string, string> = {
    forme: 'Forme',
    style: 'Style',
    technique: 'Technique',
    embellissement: 'Embellissement',
  };

  function libelle(correction: CorrectionBarre): string {
    return correction.titre || `${LIBELLES_PHASES[correction.phase] ?? correction.phase} — ${correction.type}`;
  }
</script>

<aside class="barre-laterale" aria-label="Détails des corrections">
  {#if active}
    <section class="barre-section barre-section--detail">
      <h3>Détail de la correction</h3>
      <h4 class="barre-detail__titre">{libelle(active)}</h4>
      <p class="barre-detail__explication">{active.explication}</p>
      {#if active.regle}
        <p class="barre-detail__regle">
          <strong>Règle :</strong> {active.regle}
        </p>
      {/if}
      {#if active.etat === 'obsolete'}
        <p class="barre-detail__obsolete">
          ⛔ {active.motif || 'Correction obsolète — réévaluez le paragraphe.'}
        </p>
      {/if}
    </section>
  {/if}

  <section class="barre-section">
    <h3>Corrections ({corrections.length})</h3>
    {#if corrections.length === 0}
      <p class="barre-vide">Aucune correction.</p>
    {:else}
      <ul class="barre-liste">
        {#each corrections as correction (correction.id)}
          <li>
            <button
              type="button"
              class="barre-ligne"
              class:barre-ligne--active={active?.id === correction.id}
              onclick={() => onSelectionnerGroupe(correction.groupe)}
            >
              <span class="barre-ligne__titre">{libelle(correction)}</span>
              <span class="barre-ligne__detail">
                {#if correction.phase === 'forme' && correction.decision === 'original'}
                  « {correction.original} » gardé
                {:else if correction.phase === 'forme'}
                  « {correction.correction} »
                {:else if correction.paragraphe_id}
                  paragraphe {correction.paragraphe_id.replace('p-', '')}
                {/if}
              </span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
</aside>

<style>
  .barre-laterale {
    display: grid;
    gap: 1rem;
    align-content: start;
    max-height: calc(100vh - 10rem);
    overflow-y: auto;
    padding-right: 0.25rem;
  }
  .barre-section {
    background: var(--fond-surface);
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    padding: 0.85rem;
  }
  .barre-section h3 {
    margin: 0 0 0.6rem;
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--encre-douce);
  }
  .barre-detail__titre {
    margin: 0 0 0.3rem;
    font-size: 1rem;
  }
  .barre-detail__explication,
  .barre-detail__regle {
    margin: 0 0 0.35rem;
    font-size: 0.92rem;
  }
  .barre-detail__obsolete {
    margin: 0;
    color: var(--erreur);
    font-size: 0.85rem;
  }
  .barre-vide {
    margin: 0;
    color: var(--encre-douce);
    font-style: italic;
    font-size: 0.9rem;
  }
  .barre-liste {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.4rem;
  }
  .barre-ligne {
    width: 100%;
    text-align: left;
    font: inherit;
    font-size: 0.9rem;
    padding: 0.45rem 0.6rem;
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    background: var(--fond-page);
    color: var(--encre);
    cursor: pointer;
    display: grid;
    gap: 0.15rem;
  }
  .barre-ligne:hover {
    border-color: var(--accent);
  }
  .barre-ligne--active {
    border-color: var(--accent);
    background: var(--accent-doux);
  }
  .barre-ligne__titre {
    font-weight: 600;
  }
  .barre-ligne__detail {
    color: var(--encre-douce);
    font-size: 0.85rem;
  }
</style>