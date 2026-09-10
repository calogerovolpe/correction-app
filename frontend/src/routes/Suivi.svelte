<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import Badge from '../lib/composants/Badge.svelte';
  import Bandeau from '../lib/composants/Bandeau.svelte';
  import Carte from '../lib/composants/Carte.svelte';
  import IndicateurChargement from '../lib/composants/IndicateurChargement.svelte';
  import { ErreurApiApp } from '../lib/api/client';
  import { statutAnalyse } from '../lib/api/analyses';
  import type { AnalyseSuivi, StatutAnalyse } from '../lib/api/types';

  /** Suivi E4 (jalon F2) : polling du job asynchrone avec statuts EXPLICITES
   *  (en_attente → en_cours → terminee | echec | rejetee). Le fail-fast et
   *  l'Option B sont affichés verbatim depuis `erreur` — jamais de statut
   *  fantôme : statut inconnu = erreur, pas de spinner infini. */

  interface Props {
    analyseId: number;
    periodePolling?: number;
  }

  let { analyseId, periodePolling = 2000 }: Props = $props();

  const STATUTS_FINAUX = new Set<StatutAnalyse>(['terminee', 'echec', 'rejetee']);

  const DISPOSITIONS: Record<
    StatutAnalyse,
    { libelle: string; variante: 'neutre' | 'info' | 'success' | 'attention' | 'danger' }
  > = {
    en_attente: { libelle: 'En attente', variante: 'neutre' },
    en_cours: { libelle: 'En cours', variante: 'info' },
    terminee: { libelle: 'Terminée', variante: 'success' },
    echec: { libelle: 'Échec', variante: 'danger' },
    rejetee: { libelle: 'Refusée', variante: 'attention' },
  };

  const LIBELLES_PHASES: Record<string, string> = {
    forme: 'Forme',
    style: 'Style',
    technique: 'Technique',
    embellissement: 'Embellissement',
  };

  let analyse: AnalyseSuivi | null = $state(null);
  let erreur = $state('');
  let chargement = $state(true);
  let minuteur: ReturnType<typeof setInterval> | undefined = $state();
  let actif = $state(true);

  function stopperPolling(): void {
    if (minuteur) {
      clearInterval(minuteur);
      minuteur = undefined;
    }
  }

  async function actualiser(): Promise<void> {
    if (!actif) return;
    try {
      const donnees = await statutAnalyse(analyseId);
      analyse = donnees;
      erreur = '';
      if (STATUTS_FINAUX.has(donnees.statut)) stopperPolling();
    } catch (e) {
      erreur = e instanceof ErreurApiApp
        ? e.message
        : 'Impossible de récupérer le statut de l’analyse.';
      stopperPolling();
    } finally {
      chargement = false;
    }
  }

  onMount(() => {
    void actualiser();
    minuteur = setInterval(() => void actualiser(), periodePolling);
  });

  onDestroy(() => {
    actif = false;
    stopperPolling();
  });

  function estInconnu(statut: string | null): boolean {
    return statut === null || !(statut in DISPOSITIONS);
  }
</script>
<section class="suivi">
  <h1>Analyse #{analyseId}</h1>

  {#if erreur}
    <Bandeau variante="erreur">{erreur}</Bandeau>
    <a class="lien-retour" href="#/soumission">Revenir à la soumission</a>
  {:else if chargement && !analyse}
    <IndicateurChargement message="Récupération du statut…" />
  {:else if analyse && estInconnu(analyse.statut)}
    <Bandeau variante="erreur">
      Statut « {analyse.statut ?? 'inconnu'} » non reconnu : aucune analyse
      fantôme — rechargez la page ou revenez à l'accueil.
    </Bandeau>
  {:else if analyse}
    <p class="suivi__statut">
      Statut : <Badge texte={DISPOSITIONS[analyse.statut].libelle} variante={DISPOSITIONS[analyse.statut].variante} />
    </p>

    {#if analyse.statut === 'en_attente' || analyse.statut === 'en_cours'}
      <p class="en-cours" role="status">
        {#if analyse.statut === 'en_attente'}
          L'analyse est en file d'attente…
        {:else}
          L'analyse est en cours — étape : <strong>{analyse.etape ?? 'préparation'}</strong>…
        {/if}
      </p>
      <p class="en-cours__aide">
        Cette page se met à jour toute seule toutes les deux secondes.
      </p>
    {:else if analyse.statut === 'terminee'}
      <Carte titre={`Analyse #${analyse.id} terminée`}>
        <p>
          Catégorie : <strong>{analyse.categorie ?? '—'}</strong> ·
          {analyse.resultat?.nb_corrections ?? 0} correction(s) active(s)
        </p>
        {#if analyse.resultat && Object.keys(analyse.resultat.par_phase).length > 0}
          <ul class="suivi__phases">
            {#each Object.entries(analyse.resultat.par_phase) as [phase, nombre] (phase)}
              <li>
                <strong>{LIBELLES_PHASES[phase] ?? phase}</strong> : {nombre}
                correction(s)
              </li>
            {/each}
          </ul>
        {/if}
        <p class="suivi__resultat-aide">
          Le document annoté s'ouvre dans l'atelier de relecture.
        </p>
        <a class="lien-resultat" href="#/atelier/{analyse.id}">Ouvrir le résultat</a>
      </Carte>
    {:else}
      <Bandeau variante={analyse.statut === 'rejetee' ? 'avertissement' : 'erreur'}>
        {analyse.erreur ?? "Aucun message d'erreur."}
      </Bandeau>
    {/if}
  {/if}
</section>
<style>
  .suivi {
    display: grid;
    gap: 1.25rem;
  }
  .suivi h1 {
    margin: 0;
    font-size: 1.6rem;
  }
  .lien-retour {
    font-weight: 600;
  }
  .suivi__statut {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 0;
  }
  .en-cours {
    margin: 0;
    font-size: 1.05rem;
  }
  .en-cours__aide {
    margin: 0;
    color: var(--encre-douce);
    font-size: 0.9rem;
  }
  .suivi__phases {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.35rem;
  }
  .suivi__phases li {
    font-size: 0.95rem;
  }
  .suivi__resultat-aide {
    margin: 0 0 0.75rem;
    color: var(--encre-douce);
    font-size: 0.9rem;
  }
  .lien-resultat {
    display: inline-block;
    font: inherit;
    font-size: 0.95rem;
    line-height: 1.2;
    padding: 0.5rem 1rem;
    border-radius: var(--rayon);
    background: var(--accent);
    border: 1px solid var(--accent);
    color: #fffdf8;
    text-decoration: none;
    cursor: pointer;
  }
  .lien-resultat:hover {
    background: var(--accent-fonce);
    border-color: var(--accent-fonce);
  }
</style>