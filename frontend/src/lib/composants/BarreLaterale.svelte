<script lang="ts">
  import type { CorrectionBarre } from '../api/types';
  import { decouperTrame } from '../pedagogie';

  /** Barre latérale de l'atelier (F3, enrichie FA7 — restitution pédagogique) :
   *  liste des corrections + détail enrichi (diff « Fragment d'origine →
   *  Proposition », badge/cartouche pour la règle, trame pédagogique
   *  Cause → Règle → Correction → Effet) ; STICKY et autonome au défilement ;
   *  la ligne active défile dans la vue quand la correction change (liaison
   *  texte ↔ explication) ; boutons Appliquer/Garder = alternative accessible
   *  (clavier/tactile) au clic droit. */

  interface Props {
    corrections: CorrectionBarre[];
    active: CorrectionBarre | null;
    onSelectionnerGroupe: (groupe: string, origine?: 'texte' | 'barre') => void;
    /** FA7 — alternative accessible au clic droit : appliquer la correction
     *  Forme (decision 'corrige') ou garder l'original depuis le détail. */
    onChoisirForme: (correctionId: string, decision: 'corrige' | 'original') => void;
  }

  let { corrections, active, onSelectionnerGroupe, onChoisirForme }: Props = $props();

  let aside: HTMLElement | null = null;

  const LIBELLES_PHASES: Record<string, string> = {
    forme: 'Forme',
    style: 'Style',
    technique: 'Technique',
    embellissement: 'Embellissement',
  };

  function libelle(correction: CorrectionBarre): string {
    return correction.titre || `${LIBELLES_PHASES[correction.phase] ?? correction.phase} — ${correction.type}`;
  }

  /** FA7 — diff affiché seulement quand la correction RÉÉCRIT le fragment ;
   *  Style/Technique marquent sans réécrire (original == correction) : le
   *  fragment est alors présenté comme « signalé », pas comme diff. */
  const diff = $derived.by(() => {
    if (!active || !active.correction || active.correction === active.original) {
      return null;
    }
    return { original: active.original, proposition: active.correction };
  });

  /** FA7 — trame pédagogique Cause/Règle/Correction/Effet (FA5) ; repli brut. */
  const trame = $derived(active ? decouperTrame(active.explication) : null);

  /** FA7 — le détail suit la correction active : la ligne correspondante
   *  défile doucement dans la vue (block: nearest) si la liste est longue —
   *  l'explication reste alignée avec la marque sélectionnée dans le texte. */
  $effect(() => {
    const id = active?.id;
    if (!id || !aside) return;
    const ligne = aside.querySelector('.barre-ligne--active');
    if (ligne && typeof ligne.scrollIntoView === 'function') {
      ligne.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  });
</script>

<aside class="barre-laterale" aria-label="Détails des corrections" bind:this={aside}>
  {#if active}
    <section class="barre-section barre-section--detail">
      <h3>Détail de la correction</h3>
      <h4 class="barre-detail__titre">{libelle(active)}</h4>

      {#if diff}
        <div class="barre-detail__diff">
          <div class="barre-diff">
            <span class="barre-diff__etiquette">Fragment d'origine</span>
            <span class="barre-diff__valeur barre-diff__valeur--origine">« {diff.original} »</span>
          </div>
          <span class="barre-diff__fleche" aria-hidden="true">→</span>
          <div class="barre-diff">
            <span class="barre-diff__etiquette">Proposition</span>
            <span class="barre-diff__valeur barre-diff__valeur--proposition">« {diff.proposition} »</span>
          </div>
        </div>
      {:else if active.correction}
        <div class="barre-detail__diff">
          <div class="barre-diff">
            <span class="barre-diff__etiquette">Fragment signalé</span>
            <span class="barre-diff__valeur barre-diff__valeur--signale">« {active.original} »</span>
          </div>
        </div>
      {/if}

      {#if active.regle}
        <p class="barre-detail__regle">
          <span class="badge-regle">Règle</span>
          {active.regle}
        </p>
      {/if}

      {#if trame}
        <dl class="barre-trame">
          {#if trame.cause}
            <div class="barre-trame__temps">
              <dt>Cause</dt>
              <dd>{trame.cause}</dd>
            </div>
          {/if}
          {#if trame.regle}
            <div class="barre-trame__temps">
              <dt>Règle</dt>
              <dd>{trame.regle}</dd>
            </div>
          {/if}
          {#if trame.correction}
            <div class="barre-trame__temps">
              <dt>Correction</dt>
              <dd>{trame.correction}</dd>
            </div>
          {/if}
          {#if trame.effet}
            <div class="barre-trame__temps">
              <dt>Effet</dt>
              <dd>{trame.effet}</dd>
            </div>
          {/if}
        </dl>
      {:else}
        <p class="barre-detail__explication">{active.explication}</p>
      {/if}

      {#if active.phase === 'forme' && active.etat === 'active'}
        <div class="barre-detail__actions">
          <button
            type="button"
            class="barre-bouton"
            onclick={() => onChoisirForme(active.id, 'corrige')}
          >
            ✔ Appliquer la correction
          </button>
          <button
            type="button"
            class="barre-bouton barre-bouton--secondaire"
            onclick={() => onChoisirForme(active.id, 'original')}
          >
            Garder l'original
          </button>
        </div>
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
      <!-- F4 — état vide chaleureux : un onglet sans correction est une bonne
           nouvelle, on le dit en toutes lettres (et en douceur). -->
      <p class="barre-vide" role="status">
        Rien à relire ici — votre texte est limpide sur cet onglet.
      </p>
    {:else}
      <ul class="barre-liste">
        {#each corrections as correction (correction.id)}
          <li>
            <button
              type="button"
              class="barre-ligne"
              class:barre-ligne--active={active?.id === correction.id}
              data-barre-id={correction.id}
              onclick={() => onSelectionnerGroupe(correction.groupe, 'barre')}
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
  /* FA7 — barre latérale STICKY et autonome au défilement : le manuscrit
     défile pendant que les explications restent accessibles sous les yeux.
     Repli statique sur écrans étroits (grille à une colonne de l'atelier). */
  .barre-laterale {
    position: sticky;
    top: 1rem;
    display: grid;
    gap: 1rem;
    align-content: start;
    max-height: calc(100vh - 2rem);
    overflow-y: auto;
    padding-right: 0.25rem;
  }
  @media (max-width: 900px) {
    .barre-laterale {
      position: static;
      max-height: none;
      overflow: visible;
    }
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
    margin: 0 0 0.45rem;
    font-size: 1rem;
  }
  /* FA7 — diff « Fragment d'origine → Proposition » avec repères intuitifs. */
  .barre-detail__diff {
    display: flex;
    align-items: stretch;
    gap: 0.5rem;
    margin: 0 0 0.5rem;
  }
  .barre-diff {
    flex: 1;
    display: grid;
    gap: 0.15rem;
    align-content: start;
    min-width: 0;
  }
  .barre-diff__etiquette {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--encre-douce);
    font-weight: 600;
  }
  .barre-diff__valeur {
    font-size: 0.9rem;
    border-radius: var(--rayon);
    padding: 0.25rem 0.45rem;
    overflow-wrap: anywhere;
  }
  .barre-diff__valeur--origine {
    background: var(--fond-page);
    border: 1px dashed var(--bordure);
    color: var(--corr-forme-texte);
    text-decoration: line-through;
  }
  .barre-diff__valeur--proposition {
    background: var(--corr-embellissement-fond);
    color: var(--corr-embellissement-texte);
    font-weight: 600;
  }
  .barre-diff__valeur--signale {
    background: var(--fond-page);
    border: 1px dotted var(--bordure);
    color: var(--encre);
  }
  .barre-diff__fleche {
    align-self: center;
    color: var(--encre-douce);
    font-size: 1rem;
  }
  .barre-detail__regle {
    margin: 0 0 0.45rem;
    font-size: 0.92rem;
  }
  /* FA7 — trame pédagogique en 4 temps (FA5) : Cause → Règle → Correction → Effet. */
  .barre-trame {
    margin: 0 0 0.4rem;
    display: grid;
    gap: 0.45rem;
    border-left: 3px solid var(--accent-doux);
    padding-left: 0.6rem;
  }
  .barre-trame__temps dt {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--accent-fonce);
  }
  .barre-trame__temps dd {
    margin: 0.05rem 0 0;
    font-size: 0.88rem;
    line-height: 1.45;
  }
  .barre-detail__explication {
    margin: 0 0 0.35rem;
    font-size: 0.92rem;
  }
  /* FA7 — alternative accessible au clic droit (clavier/tactile). */
  .barre-detail__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin: 0.4rem 0 0;
  }
  .barre-bouton {
    font: inherit;
    font-size: 0.82rem;
    padding: 0.3rem 0.6rem;
    border-radius: var(--rayon);
    border: 1px solid var(--succes);
    background: var(--corr-embellissement-fond);
    color: var(--succes);
    cursor: pointer;
  }
  .barre-bouton--secondaire {
    border-color: var(--bordure);
    background: var(--fond-page);
    color: var(--encre);
  }
  .barre-bouton--secondaire:hover {
    border-color: var(--encre-douce);
  }
  .barre-detail__obsolete {
    margin: 0.4rem 0 0;
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