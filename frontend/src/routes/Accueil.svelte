<script lang="ts">
  import { onMount } from 'svelte';
  import Badge from '../lib/composants/Badge.svelte';
  import Bouton from '../lib/composants/Bouton.svelte';
  import Carte from '../lib/composants/Carte.svelte';
  import EtatVide from '../lib/composants/EtatVide.svelte';
  import IndicateurChargement from '../lib/composants/IndicateurChargement.svelte';
  import Modale from '../lib/composants/Modale.svelte';
  import { ErreurApiApp } from '../lib/api/client';
  import { activerProjet, analysesRecentes, creerProjet, listerProjets, supprimerProjet } from '../lib/api/projets';
  import { naviguer } from '../lib/router';
  import { toastErreur, toastSucces } from '../lib/toasts';
  import type { AnalyseLigne, Projet, StatutAnalyse } from '../lib/api/types';

  /** Accueil & projets E1 (jalon F1, finitions F4) : liste des manuscrits,
   *  création, activation, suppression avec confirmation, analyses récentes,
   *  états vides soignés ; les retours d'actions passent par les toasts
   *  accessibles (succès polis, erreurs assertives). */

  let projets: Projet[] = $state([]);
  let analyses: AnalyseLigne[] = $state([]);
  let chargement = $state(true);
  let erreur = $state('');

  let titre = $state('');
  let creationEnCours = $state(false);
  let suppressionEnCours = $state(false);
  let projetASupprimer: Projet | null = $state(null);

  async function charger(): Promise<void> {
    chargement = true;
    erreur = '';
    try {
      const [reponseProjets, reponseAnalyses] = await Promise.all([
        listerProjets(),
        analysesRecentes(),
      ]);
      projets = reponseProjets.projets;
      analyses = reponseAnalyses.analyses;
    } catch (e) {
      erreur = e instanceof ErreurApiApp ? e.message : 'Impossible de charger vos projets.';
    } finally {
      chargement = false;
    }
  }

  onMount(charger);

  async function creer(): Promise<void> {
    const nouveauTitre = titre.trim();
    if (!nouveauTitre || creationEnCours) return;
    creationEnCours = true;
    try {
      await creerProjet(nouveauTitre);
      titre = '';
      toastSucces(`Projet « ${nouveauTitre} » créé — à vos plumes !`);
      await charger();
    } catch (e) {
      toastErreur(e instanceof ErreurApiApp ? e.message : 'La création du projet a échoué.');
    } finally {
      creationEnCours = false;
    }
  }

  async function activer(projet: Projet): Promise<void> {
    try {
      await activerProjet(projet.projet_id);
      toastSucces(`« ${projet.titre} » est maintenant le projet actif.`);
      await charger();
    } catch (e) {
      toastErreur(e instanceof ErreurApiApp ? e.message : "L'activation du projet a échoué.");
    }
  }

  /** FA2 — bouton « Ouvrir » : entre dans le manuscrit. Une analyse terminée
   *  ouvre l'atelier E5 directement ; un projet encore vierge mène à la
   *  soumission du premier texte. Le projet est activé au passage (une seule
   *  opération : l'activation puis la navigation). */
  async function ouvrir(projet: Projet): Promise<void> {
    try {
      if (!projet.actif) {
        await activerProjet(projet.projet_id);
      }
      if (projet.derniere_analyse_id !== null) {
        naviguer(`/atelier/${projet.derniere_analyse_id}`);
      } else {
        naviguer('/soumission');
      }
    } catch (e) {
      toastErreur(e instanceof ErreurApiApp ? e.message : "L'ouverture du projet a échoué.");
    }
  }

  async function confirmerSuppression(): Promise<void> {
    if (!projetASupprimer || suppressionEnCours) return;
    suppressionEnCours = true;
    const cible = projetASupprimer;
    try {
      await supprimerProjet(cible.projet_id);
      projetASupprimer = null;
      toastSucces(`Projet « ${cible.titre} » supprimé.`);
      await charger();
    } catch (e) {
      toastErreur(e instanceof ErreurApiApp ? e.message : 'La suppression du projet a échoué.');
      projetASupprimer = null;
    } finally {
      suppressionEnCours = false;
    }
  }

  function chaineLibelle(projet: Projet): string {
    switch (projet.chain_status) {
      case 'ok':
        return 'chaîne cohérente';
      case 'rupture':
        return 'rupture de chaîne';
      default:
        return 'chaîne vierge';
    }
  }

  function chaineVariante(projet: Projet): 'neutre' | 'success' | 'danger' {
    switch (projet.chain_status) {
      case 'ok':
        return 'success';
      case 'rupture':
        return 'danger';
      default:
        return 'neutre';
    }
  }

  const DISPOSITIONS: Record<
    StatutAnalyse,
    { libelle: string; variante: 'neutre' | 'info' | 'success' | 'attention' | 'danger' }
  > = {
    en_attente: { libelle: 'en attente', variante: 'neutre' },
    en_cours: { libelle: 'en cours', variante: 'info' },
    terminee: { libelle: 'terminée', variante: 'success' },
    echec: { libelle: 'échec', variante: 'danger' },
    rejetee: { libelle: 'rejetée', variante: 'attention' },
  };

  function disposition(statut: StatutAnalyse) {
    return DISPOSITIONS[statut];
  }
</script>

<section class="accueil">
  <h1>Bienvenue dans votre atelier de correction</h1>
  <p class="accueil__intro">
    Relisez votre manuscrit en douceur : chaque texte soumis est analysé puis présenté
    dans un atelier de relecture, corrections en couleur et à votre main.
  </p>

  {#if erreur}
    <p class="alerte alerte--erreur" role="alert">{erreur}</p>
    <Bouton variante="secondaire" onclick={() => void charger()}>Réessayer</Bouton>
  {:else if chargement && projets.length === 0}
    <IndicateurChargement message="Chargement de vos projets…" />
  {:else}
    <Carte titre="Vos manuscrits">
      {#if projets.length === 0}
        {#snippet ctaPremierProjet()}
          <Bouton
            variante="primaire"
            onclick={() => document.getElementById('titre-projet')?.focus()}
          >
            Créer mon premier projet
          </Bouton>
        {/snippet}
        <EtatVide
          titre="Aucun manuscrit pour le moment"
          message="Créez votre premier projet (votre roman) pour commencer à le corriger."
          illustration="📖"
          action={ctaPremierProjet}
        />
      {:else}
        <ul class="projets">
          {#each projets as projet (projet.projet_id)}
            <li class="projets__projet">
              <div class="projets__infos">
                <span class="projets__titre">{projet.titre}</span>
                <Badge texte={chaineLibelle(projet)} variante={chaineVariante(projet)} />
                {#if projet.actif}
                  <Badge texte="actif" variante="success" />
                {/if}
                {#if projet.current_chapter_num !== null}
                  <span class="projets__detail">
                    {#if projet.current_chapter_num === 0}Prologue{:else}Chapitre {projet.current_chapter_num}{/if}
                    {#if projet.last_chapter_title} — {projet.last_chapter_title}{/if}
                  </span>
                {/if}
              </div>
              <div class="projets__actions">
                <Bouton
                  variante="primaire"
                  title={projet.derniere_analyse_id !== null
                    ? "Ouvrir le dernier résultat dans l'atelier"
                    : "Ouvrir le projet et soumettre un premier texte"}
                  onclick={() => void ouvrir(projet)}
                >
                  Ouvrir
                </Bouton>
                {#if !projet.actif}
                  <Bouton variante="secondaire" onclick={() => void activer(projet)}>Activer</Bouton>
                {/if}
                <Bouton
                  variante="danger"
                  desactive={projet.actif}
                  title={projet.actif ? "Le projet actif ne peut pas être supprimé — activez d'abord un autre projet." : undefined}
                  onclick={() => {
                    projetASupprimer = projet;
                  }}
                >
                  Supprimer
                </Bouton>
              </div>
            </li>
          {/each}
        </ul>
      {/if}
    </Carte>

<Carte titre="Créer un nouveau projet">
      <form
        class="creation"
        onsubmit={(evenement) => {
          evenement.preventDefault();
          void creer();
        }}
      >
        <label class="creation__label" for="titre-projet">Titre du roman</label>
        <div class="creation__ligne">
          <input
            id="titre-projet"
            class="creation__champ"
            type="text"
            maxlength="200"
            bind:value={titre}
            placeholder="Ex. : Les jardins d'Aria"
          />
          <Bouton type="submit" desactive={creationEnCours || !titre.trim()}>Créer le projet</Bouton>
        </div>
      </form>
    </Carte>

    <Carte titre="Analyses récentes">
      {#if analyses.length === 0}
        <EtatVide
          titre="Aucune analyse récente"
          message="Vos prochaines analyses apparaîtront ici : soumettez un texte depuis « Soumettre un texte » pour le voir relu dans l'atelier."
          illustration="📚"
        />
      {:else}
        <ul class="analyses">
          {#each analyses as analyse (analyse.id)}
            <li class="analyses__ligne">
              <!-- FA2 : une analyse terminée ouvre l'atelier E5 ; les autres
                   mènent au suivi (jamais de route hors SPA). -->
              <a class="analyses__lien" href={analyse.statut === 'terminee'
                ? `#/atelier/${analyse.id}`
                : `#/analyses/${analyse.id}`}># {analyse.id}</a>
              <Badge texte={disposition(analyse.statut).libelle} variante={disposition(analyse.statut).variante} />
              {#if analyse.categorie}
                <span class="analyses__categorie">{analyse.categorie}</span>
              {/if}
              {#if analyse.extrait}
                <span class="analyses__extrait">« {analyse.extrait}… »</span>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    </Carte>
  {/if}

  {#if projetASupprimer}
    <Modale
      titre={`Supprimer le projet « ${projetASupprimer.titre} » ?`}
      message="Cette action est définitive : toutes les analyses, corrections et notes liées à ce projet seront effacées."
      annuler="Annuler"
      confirmer={suppressionEnCours ? 'Suppression…' : 'Supprimer définitivement'}
      onFermer={() => {
        projetASupprimer = null;
      }}
      onConfirmer={() => void confirmerSuppression()}
    />
  {/if}
</section>

<style>
  .accueil {
    display: grid;
    gap: 1.5rem;
  }
  .accueil h1 {
    margin: 0;
    font-size: 1.6rem;
  }
  .accueil__intro {
    margin: 0;
    max-width: 60ch;
    color: var(--encre-douce);
  }
  .alerte {
    margin: 0;
    padding: 0.6rem 0.85rem;
    border-radius: var(--rayon);
    font-size: 0.95rem;
  }
  .alerte--erreur {
    color: var(--erreur);
    background: var(--corr-forme-fond);
    border: 1px solid var(--erreur);
  }
  .projets {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.75rem;
  }
  .projets__projet {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    padding: 0.65rem 0.85rem;
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    background: var(--fond-page);
  }
  .projets__infos {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .projets__titre {
    font-weight: 600;
  }
  .projets__detail {
    color: var(--encre-douce);
    font-size: 0.9rem;
  }
  .projets__actions {
    display: flex;
    gap: 0.5rem;
  }
  .creation__label {
    display: block;
    margin-bottom: 0.4rem;
    font-weight: 600;
  }
  .creation__ligne {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .creation__champ {
    flex: 1 1 18rem;
    font: inherit;
    padding: 0.5rem 0.7rem;
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    background: var(--fond-surface);
    color: var(--encre);
  }
  .creation__champ:focus {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }
  .analyses {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.5rem;
  }
  .analyses__ligne {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
    font-size: 0.95rem;
  }
  .analyses__lien {
    font-weight: 600;
  }
  .analyses__categorie {
    color: var(--encre-douce);
  }
  .analyses__extrait {
    color: var(--encre-douce);
    font-style: italic;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 34ch;
  }

  /* F4 — mobile : les actions de projet passent en colonne tactile (cibles
     confortables, pas de chevauchement), l'extrait d'analyse s'élargit. */
  @media (max-width: 640px) {
    .projets__projet {
      flex-direction: column;
      align-items: stretch;
    }
    .projets__actions {
      flex-wrap: wrap;
    }
    .projets__actions :global(.bouton) {
      flex: 1 1 auto;
    }
    .analyses__extrait {
      max-width: 100%;
    }
  }
</style>