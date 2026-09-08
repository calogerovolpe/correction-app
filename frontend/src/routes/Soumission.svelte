<script lang="ts">
  import { onMount } from 'svelte';
  import Bandeau from '../lib/composants/Bandeau.svelte';
  import Bouton from '../lib/composants/Bouton.svelte';
  import EditeurWord from '../lib/composants/EditeurWord.svelte';
  import EtatVide from '../lib/composants/EtatVide.svelte';
  import { ErreurApiApp } from '../lib/api/client';
  import { preparerSoumission, soumettreAnalyse } from '../lib/api/analyses';
  import { naviguer } from '../lib/router';
  import type { CategorieAnalyse, PhasesSelection, PreparerSoumission } from '../lib/api/types';

  /** Soumission E3 (jalon F2) : collage Word fidèle, catégorie, numéro N+1
   *  pré-rempli, matrice de phases dérogable, compteur 30 000 caractères,
   *  refus explicites (jamais de troncature silencieuse). */

  let preparation: PreparerSoumission | null = $state(null);
  let chargement = $state(true);
  let erreurPreparation = $state('');

  let categorie: CategorieAnalyse = $state('chapitre');
  let phases: PhasesSelection = $state({ forme: true, style: true, technique: true });
  let numeroChapitre = $state('');
  let avecCodex = $state(true);

  let texteV2 = $state('');
  let compteur = $state(0);
  let soumissionEnCours = $state(false);
  let erreurSoumission = $state('');

  function matricesParCategorie(choisie: CategorieAnalyse): PhasesSelection {
    // Pré-sélection dérogable (decision J2.1) : Chapitre = Forme + Style +
    // Technique ; Passage/Extrait = Forme + Style.
    return {
      forme: true,
      style: true,
      technique: choisie === 'chapitre',
    };
  }

  function afficherNumero(valeur: number): string {
    return String(valeur);
  }

  async function chargerPreparation(): Promise<void> {
    chargement = true;
    erreurPreparation = '';
    try {
      const donnees = await preparerSoumission();
      preparation = donnees;
      categorie = donnees.prefil.categorie;
      // Mémoire J2.5 : les dernières configurations s'affichent telles quelles.
      phases = { ...donnees.prefil.phases };
      numeroChapitre = afficherNumero(donnees.numero_attendu);
    } catch (e) {
      erreurPreparation = e instanceof ErreurApiApp
        ? e.message
        : 'Impossible de préparer la soumission.';
    } finally {
      chargement = false;
    }
  }

  onMount(chargerPreparation);

  function choisirCategorie(choisie: CategorieAnalyse): void {
    if (choisie === categorie) return;
    categorie = choisie;
    // La matrice ne fait que pré-cocher : un changement de catégorie
    // réinitialise la pré-sélection (comportement identique à E3 Jinja2).
    phases = matricesParCategorie(choisie);
  }

  function numeroSaisi(): number | null {
    const brut = numeroChapitre.trim();
    if (!brut) return null;
    const valeur = Number(brut);
    return Number.isNaN(valeur) ? null : valeur;
  }

  function indicateurNumero(): string {
    const attendu = preparation?.numero_attendu;
    if (attendu === undefined) return '';
    const saisi = numeroSaisi();
    if (saisi !== null && saisi !== attendu) {
      return `(attendu : ${afficherNumero(attendu)} — vous avez saisi ${numeroChapitre.trim()})`;
    }
    return `(attendu par la suite : ${afficherNumero(attendu)})`;
  }

  function surplusCaracteres(): number {
    const max = preparation?.max_caracteres ?? 30000;
    return compteur > max ? compteur - max : 0;
  }

  async function soumettre(): Promise<void> {
    if (soumissionEnCours || compteur === 0) return;
    soumissionEnCours = true;
    erreurSoumission = '';
    try {
      const suivi = await soumettreAnalyse({
        texte: texteV2,
        categorie,
        numero_chapitre: categorie === 'chapitre' ? numeroSaisi() : null,
        avec_codex: avecCodex && categorie === 'chapitre',
        phases,
      });
      naviguer(`/analyses/${suivi.id}`);
    } catch (e) {
      erreurSoumission = e instanceof ErreurApiApp
        ? e.message
        : 'La soumission du texte a échoué.';
    } finally {
      soumissionEnCours = false;
    }
  }
</script>
<section class="soumission">
  <h1>Soumettre un texte</h1>

  {#if erreurPreparation}
    <Bandeau variante="erreur">{erreurPreparation}</Bandeau>
    <Bouton variante="secondaire" onclick={() => void chargerPreparation()}>Réessayer</Bouton>
  {:else if chargement}
    <p class="chargement" role="status">Préparation du formulaire…</p>
  {:else if preparation && !preparation.projet}
    <EtatVide
      titre="Aucun projet actif"
      message="Créez d'abord un projet (votre roman) sur la page d'accueil, puis revenez soumettre votre texte."
    >
      {#snippet action()}
        <a class="lien-retour" href="#/">Revenir à l'accueil</a>
      {/snippet}
    </EtatVide>
  {:else if preparation}
    <p class="soumission__projet">
      Projet actif : <strong>{preparation.projet?.titre}</strong> ({preparation.projet?.projet_id})
      — chaîne : {preparation.projet?.chain_status}
    </p>

    {#if erreurSoumission}
      <Bandeau variante="erreur">{erreurSoumission}</Bandeau>
    {/if}

    <form
      onsubmit={(evenement) => {
        evenement.preventDefault();
        void soumettre();
      }}
    >
      <EditeurWord bind:valeur={texteV2} bind:compteur={compteur} />

      <p class="compteur-taille">
        <span class={surplusCaracteres() > 0 ? 'compteur-taille--depassement' : ''}>
          {compteur} / {preparation.max_caracteres} caractères
        </span>
        — au-delà : refus explicite, jamais de troncature.
      </p>
      {#if surplusCaracteres() > 0}
        <p class="depassement" role="alert">
          Dépassez de {surplusCaracteres()} caractères la limite de
          {preparation.max_caracteres} : la soumission sera refusée.
        </p>
      {/if}

      <fieldset class="soumission__groupe">
        <legend>Catégorie du texte</legend>
        <label>
          <input type="radio" name="categorie" value="chapitre" checked={categorie === 'chapitre'}
                 onchange={() => choisirCategorie('chapitre')} />
          <strong>Chapitre</strong> (officiel ou brouillon)
        </label>
        <label>
          <input type="radio" name="categorie" value="passage" checked={categorie === 'passage'}
                 onchange={() => choisirCategorie('passage')} />
          <strong>Passage</strong> (scène libre, aucune écriture narrative)
        </label>
        <label>
          <input type="radio" name="categorie" value="extrait" checked={categorie === 'extrait'}
                 onchange={() => choisirCategorie('extrait')} />
          <strong>Extrait</strong> (court fragment, aucune écriture narrative)
        </label>
      </fieldset>

      {#if categorie === 'chapitre'}
        <fieldset class="soumission__groupe">
          <legend>Options du Chapitre</legend>
          <div class="groupe-num-chapitre">
            <label for="numero-chapitre">Numéro du chapitre :</label>
            <input id="numero-chapitre" type="number" step="1" min="0" bind:value={numeroChapitre} />
            <span class="indicateur-attendu">{indicateurNumero()}</span>
          </div>
          <label class="soumission__ligne-case">
            <input type="checkbox" bind:checked={avecCodex} />
            <strong>Mettre à jour le Codex et les Journaux</strong> lors de la validation officielle
          </label>
          <p class="aide">
            Si coché, les fiches de personnages, glossaires et évolutions seront
            extraits et enregistrés quand vous validerez ce chapitre.
          </p>
        </fieldset>
      {/if}

      <fieldset class="soumission__groupe">
        <legend>Types de correction</legend>
        <label class="soumission__ligne-case">
          <input type="checkbox" bind:checked={phases.forme} />
          <strong>Forme</strong> — orthographe, grammaire, typographie (barré conservé)
        </label>
        <label class="soumission__ligne-case">
          <input type="checkbox" bind:checked={phases.style} />
          <strong>Style</strong> — répétitions, lourdeurs (alternatives à la demande)
        </label>
        <label class="soumission__ligne-case">
          <input type="checkbox" bind:checked={phases.technique} />
          <strong>Technique</strong> — temps, POV, cohérence (fond jaune + barre latérale)
        </label>
        <p class="aide">
          L'Embellissement se demande à tout moment : sélectionnez un passage
          dans le résultat, puis clic droit → « Embellir la sélection ».
        </p>
      </fieldset>

      <Bouton type="submit" desactive={soumissionEnCours || compteur === 0}>
        {soumissionEnCours ? 'Soumission en cours…' : "Lancer l'analyse"}
      </Bouton>
    </form>
  {/if}
</section>
<style>
  .soumission {
    display: grid;
    gap: 1.25rem;
  }
  .soumission h1 {
    margin: 0;
    font-size: 1.6rem;
  }
  .chargement {
    color: var(--encre-douce);
    font-style: italic;
  }
  .lien-retour {
    font-weight: 600;
  }
  .soumission__projet {
    margin: 0;
    color: var(--encre-douce);
  }
  .compteur-taille {
    margin: 0.4rem 0 0;
    font-size: 0.95rem;
    color: var(--encre-douce);
  }
  .compteur-taille--depassement {
    color: var(--erreur);
    font-weight: 700;
  }
  .depassement {
    margin: 0;
    color: var(--erreur);
    background: var(--corr-forme-fond);
    border: 1px solid var(--erreur);
    border-radius: var(--rayon);
    padding: 0.5rem 0.75rem;
    font-size: 0.95rem;
  }
  .soumission__groupe {
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    background: var(--fond-surface);
    padding: 0.9rem 1rem;
    display: grid;
    gap: 0.5rem;
  }
  .soumission__groupe legend {
    font-weight: 600;
    padding: 0 0.4rem;
  }
  .soumission__groupe label {
    font-size: 0.98rem;
    line-height: 1.4;
  }
  .soumission__ligne-case {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.5rem;
    align-items: start;
  }
  .groupe-num-chapitre {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
  }
  .groupe-num-chapitre input {
    width: 6rem;
    font: inherit;
    padding: 0.4rem 0.55rem;
    border: 1px solid var(--bordure);
    border-radius: var(--rayon);
    background: var(--fond-surface);
    color: var(--encre);
  }
  .indicateur-attendu {
    color: var(--encre-douce);
    font-size: 0.9rem;
  }
  .aide {
    margin: 0;
    color: var(--encre-douce);
    font-size: 0.9rem;
    line-height: 1.45;
  }
</style>