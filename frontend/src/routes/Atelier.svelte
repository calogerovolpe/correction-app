<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import Bandeau from '../lib/composants/Bandeau.svelte';
  import BarreLaterale from '../lib/composants/BarreLaterale.svelte';
  import Bouton from '../lib/composants/Bouton.svelte';
  import DocumentAnnote from '../lib/composants/DocumentAnnote.svelte';
  import MenuContextuel, {
    type ElementMenu,
  } from '../lib/composants/MenuContextuel.svelte';
  import OngletsPhase from '../lib/composants/OngletsPhase.svelte';
  import PopoverSuggestion from '../lib/composants/PopoverSuggestion.svelte';
  import ToggleMasquer from '../lib/composants/ToggleMasquer.svelte';
  import { ErreurApiApp } from '../lib/api/client';
  import {
    alternatives,
    appliquerAlternative,
    appliquerEmbellissement,
    choisirForme,
    editerParagraphe,
    embellir,
    etatAtelier,
    nouvelleVersion,
    reevaluerParagraphe,
    validerAnalyse,
  } from '../lib/api/atelier';
  import type {
    CorrectionBarre,
    EtatAtelier,
    OngletAtelier,
    ParagrapheAnnote,
    ReponseSuggestion,
    SegmentAnnote,
  } from '../lib/api/types';
  import { naviguer } from '../lib/router';

  /** Écran E5 — Atelier de relecture (jalon F3, absorbe UX1 + UX4 + toggle
   *  d'UX2) : couches superposables, onglets par phase + compteurs, barre
   *  latérale, édition directe sans IA temps réel + « ↻ Re-corriger », menu
   *  contextuel riche, sélection + clic droit (embellissement / alternatives),
   *  navigation clavier, validation du texte affiché. */

  interface Props {
    analyseId: number;
  }

  let { analyseId }: Props = $props();

  let etat = $state<EtatAtelier | null>(null);
  let chargement = $state(true);
  let erreur = $state('');
  let success = $state('');
  let onglet = $state<OngletAtelier>('tout');
  let masque = $state(false);
  let correctionActive = $state<CorrectionBarre | null>(null);
  let enEditionId = $state<string | null>(null);
  let texteEdition = $state('');
  let menu = $state<{
    x: number;
    y: number;
    items: ElementMenu[];
    action: string | null;
  } | null>(null);
  let popover = $state<{
    type: 'embellissement' | 'alternatives';
    suggestion: ReponseSuggestion;
  } | null>(null);
  let actionEnCours = $state(false);
  let selectionContexte = $state<{
    paragrapheId: string;
    fragment: string;
    contexte: string;
    texteParagraphe: string;
  } | null>(null);

  let zone = $state<HTMLElement | null>(null);

  onMount(() => {
    document.addEventListener('mousedown', fermerSiHorsDe);
    document.addEventListener('keydown', appuiTouche);
    return () => {
      document.removeEventListener('mousedown', fermerSiHorsDe);
      document.removeEventListener('keydown', appuiTouche);
    };
  });

  // FA3 — réactivité : le chargement est piloté par le CHANGEMENT d'analyseId
  // (navigation directe entre analyses, retour sur une autre analyse). Fin de
  // l'atelier figé sur « Chargement… » quand l'identifiant change sous les pieds
  // du composant : chaque nouvelle analyse relance systématiquement le chargement.
  let analyseChargee: number | null = null;
  // FA4 — jeton anti-course : chaque chargement s'incrémente ; une réponse qui
  // revient après un chargement plus récent (clics rapides d'onglets) est
  // ignorée au lieu d'écraser l'état courant avec une projection périmée.
  let jetonChargement = 0;
  $effect(() => {
    if (analyseId !== analyseChargee) {
      analyseChargee = analyseId;
      void charger();
    }
  });

  onDestroy(() => {
    document.removeEventListener('mousedown', fermerSiHorsDe);
    document.removeEventListener('keydown', appuiTouche);
  });

  async function charger(ongletDemande?: OngletAtelier): Promise<void> {
    const jeton = ++jetonChargement;
    chargement = true;
    erreur = '';
    try {
      const nouvelEtat = await etatAtelier(analyseId, ongletDemande ?? onglet);
      if (jeton !== jetonChargement) return; // réponse périmée — on ignore
      etat = nouvelEtat;
      if (etat) {
        onglet = etat.onglet;
        reconcilierCorrectionActive();
      }
    } catch (e) {
      if (jeton !== jetonChargement) return; // réponse périmée — on ignore
      erreur =
        e instanceof ErreurApiApp ? e.message : 'Impossible de charger l’atelier.';
    } finally {
      if (jeton === jetonChargement) chargement = false;
    }
  }

  function changerOnglet(nouveau: OngletAtelier): void {
    if (nouveau !== onglet) void charger(nouveau);
  }

  function selectionnerGroupe(groupe: string): void {
    if (!etat) return;
    correctionActive =
      etat.document.corrections_barre.find((c) => c.groupe === groupe) ?? null;
  }

  /** FA4 — réconciliation PROPRE de la correction active (barre latérale) :
   *  après une mutation, la référence précédente peut être obsolète (id
   *  régénéré par une réévaluation, décision modifiée, correction devenue
   *  obsolète…). On retrouve l'id ciblé s'il existe toujours, sinon la
   *  correction courante si elle subsiste, sinon la première correction
   *  active — jamais de détail fantôme ni de liste désynchronisée. */
  function reconcilierCorrectionActive(cibleId?: string | null): void {
    if (!etat) {
      correctionActive = null;
      return;
    }
    const barre = etat.document.corrections_barre;
    if (cibleId) {
      const cible = barre.find((c) => c.id === cibleId);
      if (cible) {
        correctionActive = cible;
        return;
      }
    }
    const courante = correctionActive
      ? barre.find((c) => c.id === correctionActive?.id)
      : undefined;
    correctionActive = courante ?? barre.find((c) => c.etat === 'active') ?? null;
  }

  function paragrapheCorrige(p: ParagrapheAnnote): boolean {
    if (p.edite) return true;
    return (
      etat?.document.corrections_barre.some(
        (c) => c.paragraphe_id === p.id && c.etat === 'active',
      ) ?? false
    );
  }

  let paragraphesAffiches = $derived(
    masque && etat
      ? etat.document.paragraphes.filter(paragrapheCorrige)
      : (etat?.document.paragraphes ?? []),
  );

  function texteCourantParagraphe(paragrapheId: string): string {
    const p = etat?.document.paragraphes.find((x) => x.id === paragrapheId);
    if (!p) return '';
    return p.segments
      .map((s: SegmentAnnote) => (s.type === 'forme' ? s.ins : s.texte))
      .join('');
  }

  // --- Sélection + extraction du fragment (les <del> barrés exclus) -------------

  function extraireSelection(): string | null {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) return null;
    const plage = sel.getRangeAt(0);
    if (
      !zone ||
      !(plage.commonAncestorContainer instanceof Node) ||
      !zone.contains(plage.commonAncestorContainer)
    ) {
      return null;
    }
    const conteneur = plage.commonAncestorContainer;
    const elementConteneur =
      conteneur instanceof HTMLElement ? conteneur : conteneur.parentElement;
    const paragraphe = elementConteneur?.closest(
      '[data-paragraphe-id]',
    ) as HTMLElement | null;
    if (!paragraphe) return null;
    const paragrapheId = paragraphe.dataset.paragrapheId ?? '';
    if (!paragrapheId) return null;

    const morceaux: string[] = [];
    const marcheur = document.createTreeWalker(paragraphe, NodeFilter.SHOW_TEXT, {
      acceptNode: (noeud) =>
        noeud.parentElement && noeud.parentElement.closest('del')
          ? NodeFilter.FILTER_REJECT
          : NodeFilter.FILTER_ACCEPT,
    });
    let noeud: Node | null;
    while ((noeud = marcheur.nextNode())) {
      if (!plage.intersectsNode(noeud)) continue;
      const debut = noeud === plage.startContainer ? plage.startOffset : 0;
      const fin =
        noeud === plage.endContainer
          ? plage.endOffset
          : (noeud.textContent?.length ?? 0);
      morceaux.push((noeud.textContent ?? '').slice(debut, fin));
    }
    const fragment = morceaux.join('').replace(/\s+/g, ' ').trim();
    if (!fragment) return null;

    // Contexte (ancre de désambiguïsation) : début du paragraphe affiché.
    const avant = document.createRange();
    avant.selectNodeContents(paragraphe);
    avant.setEnd(plage.startContainer, plage.startOffset);
    const contexte = avant.toString().slice(-120).trim();

    selectionContexte = {
      paragrapheId,
      fragment,
      contexte,
      texteParagraphe: texteCourantParagraphe(paragrapheId),
    };
    return fragment;
  }

  /** Clic droit : menu contextuel RICHE (décision 36) — sur une marque
   *  (Forme : Appliquer / Garder l'original) OU sur une sélection
   *  (Embellir / Trouver une alternative). */
  function ouvrirMenu(evenement: MouseEvent): void {
    evenement.preventDefault();
    menu = null;
    popover = null;
    selectionContexte = null;

    const cible = (evenement.target as HTMLElement).closest?.(
      '[data-groupe]',
    ) as HTMLElement | null;
    if (cible) {
      const groupe = cible.dataset.groupe ?? '';
      const correction = etat?.document.corrections_barre.find(
        (c) => c.groupe === groupe,
      );
      if (correction?.phase === 'forme' && correction.etat === 'active') {
        menu = {
          x: evenement.clientX,
          y: evenement.clientY,
          items: [
            { cle: 'appliquer-forme', libelle: '✔ Appliquer la correction' },
            { cle: 'garder-original', libelle: "Garder l'original" },
          ],
          action: correction.id,
        };
        return;
      }
    }

    if (extraireSelection()) {
      menu = {
        x: evenement.clientX,
        y: evenement.clientY,
        items: [
          { cle: 'embellir', libelle: '✨ Embellir la sélection' },
          { cle: 'alternatives', libelle: '🔁 Trouver une alternative' },
        ],
        action: null,
      };
    }
  }

  function fermerSiHorsDe(evenement: MouseEvent): void {
    const cible = evenement.target as Node | null;
    if (!cible) return;
    const dansMenu = document
      .querySelector('.menu-contextuel')
      ?.contains(cible);
    const dansPopover = document.querySelector('.popover')?.contains(cible);
    if (menu && !dansMenu) menu = null;
    if (popover && !dansPopover) popover = null;
  }

  function appuiTouche(evenement: KeyboardEvent): void {
    if (evenement.key === 'Escape') {
      menu = null;
      popover = null;
      enEditionId = null;
    }
  }

  // --- Actions de l'atelier -----------------------------------------------------

  function monterErreur(e: unknown): void {
    actionEnCours = false;
    erreur =
      e instanceof ErreurApiApp ? e.message : 'Une erreur inattendue est survenue.';
  }

  async function choisir(
    actionCle: 'appliquer-forme' | 'garder-original',
  ): Promise<void> {
    if (!menu?.action || actionEnCours) return;
    const cibleId = menu.action;
    actionEnCours = true;
    erreur = '';
    success = '';
    try {
      // FA4 : l'onglet courant est transmis — la réponse re-projette CET onglet
      // (plus de saut intempestif vers « tout » après un choix Forme).
      etat = await choisirForme(
        analyseId,
        {
          correction_id: cibleId,
          decision: actionCle === 'appliquer-forme' ? 'corrige' : 'original',
        },
        onglet,
      );
      onglet = etat.onglet;
      reconcilierCorrectionActive(cibleId);
    } catch (e) {
      monterErreur(e);
    } finally {
      menu = null;
      actionEnCours = false;
    }
  }

  function appliquerActionMenu(cle: string): void {
    if (cle === 'appliquer-forme' || cle === 'garder-original') {
      void choisir(cle);
      return;
    }
    if (cle === 'embellir') void demanderEmbellissement();
    if (cle === 'alternatives') void demanderAlternatives();
  }

  async function demanderEmbellissement(): Promise<void> {
    if (!selectionContexte || actionEnCours) return;
    actionEnCours = true;
    erreur = '';
    try {
      const suggestion = await embellir({
        fragment: selectionContexte.fragment,
        paragraphe_texte: selectionContexte.texteParagraphe,
        contexte: selectionContexte.contexte,
      });
      if (suggestion.erreur) {
        erreur = suggestion.erreur;
      } else {
        popover = { type: 'embellissement', suggestion };
      }
    } catch (e) {
      monterErreur(e);
    } finally {
      actionEnCours = false;
    }
  }

  async function demanderAlternatives(): Promise<void> {
    if (!selectionContexte || actionEnCours) return;
    actionEnCours = true;
    erreur = '';
    try {
      const suggestion = await alternatives({
        fragment: selectionContexte.fragment,
        paragraphe_texte: selectionContexte.texteParagraphe,
      });
      if (suggestion.erreur) {
        erreur = suggestion.erreur;
      } else {
        popover = { type: 'alternatives', suggestion };
      }
    } catch (e) {
      monterErreur(e);
    } finally {
      actionEnCours = false;
    }
  }

  async function appliquerProposition(texte: string): Promise<void> {
    if (!selectionContexte || !popover || actionEnCours) return;
    const { paragrapheId, fragment, contexte } = selectionContexte;
    actionEnCours = true;
    erreur = '';
    success = '';
    try {
      if (popover.type === 'embellissement') {
        etat = await appliquerEmbellissement(
          analyseId,
          {
            paragraphe_id: paragrapheId,
            fragment,
            texte,
            contexte,
          },
          onglet,
        );
      } else {
        etat = await appliquerAlternative(
          analyseId,
          {
            paragraphe_id: paragrapheId,
            fragment,
            texte,
            contexte,
          },
          onglet,
        );
      }
      onglet = etat.onglet;
      reconcilierCorrectionActive();
      popover = null;
      selectionContexte = null;
    } catch (e) {
      monterErreur(e);
    } finally {
      actionEnCours = false;
    }
  }

  function demarrerEdition(paragrapheId: string): void {
    enEditionId = paragrapheId;
    texteEdition = texteCourantParagraphe(paragrapheId);
  }

  async function validerEdition(): Promise<void> {
    if (!enEditionId || actionEnCours) return;
    actionEnCours = true;
    erreur = '';
    success = '';
    try {
      etat = await editerParagraphe(analyseId, enEditionId, texteEdition, onglet);
      onglet = etat.onglet;
      reconcilierCorrectionActive();
      enEditionId = null;
      success = 'Paragraphe mis à jour.';
    } catch (e) {
      monterErreur(e);
    } finally {
      actionEnCours = false;
    }
  }

  function annulerEdition(): void {
    enEditionId = null;
    texteEdition = '';
  }

  async function reexecuterParagraphe(paragrapheId: string): Promise<void> {
    if (actionEnCours) return;
    actionEnCours = true;
    erreur = '';
    success = '';
    try {
      etat = await reevaluerParagraphe(analyseId, paragrapheId, onglet);
      onglet = etat.onglet;
      reconcilierCorrectionActive();
      success = 'Corrections du paragraphe réévaluées.';
    } catch (e) {
      monterErreur(e);
    } finally {
      actionEnCours = false;
    }
  }

  async function reexecuterNouvelleVersion(): Promise<void> {
    if (actionEnCours) return;
    actionEnCours = true;
    erreur = '';
    success = '';
    try {
      const reponse = await nouvelleVersion(analyseId);
      naviguer(`/analyses/${reponse.nouvel_id}`);
    } catch (e) {
      monterErreur(e);
    } finally {
      actionEnCours = false;
    }
  }

  async function valider(): Promise<void> {
    if (actionEnCours) return;
    actionEnCours = true;
    erreur = '';
    success = '';
    try {
      const reponse = await validerAnalyse(analyseId);
      success = `Chapitre ${reponse.titre} validé — version officielle enregistrée.`;
    } catch (e) {
      monterErreur(e);
    } finally {
      actionEnCours = false;
    }
  }

  // SENTINELLE_SCRIPT
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<section class="atelier" bind:this={zone} oncontextmenu={ouvrirMenu}>
  <header class="atelier__entete">
    <div>
      <h1 class="atelier__titre">Atelier — analyse #{analyseId}</h1>
      {#if etat}
        <p class="atelier__sous-titre">
          Catégorie : <strong>{etat.categorie ?? '—'}</strong> ·
          {etat.nb_corrections} correction(s) active(s)
        </p>
      {/if}
    </div>
    <div class="atelier__actions">
      <Bouton
        variante="secondaire"
        desactive={actionEnCours}
        onclick={() => void reexecuterNouvelleVersion()}
      >
        🔄 Re-corriger (nouvelle version)
      </Bouton>
      {#if etat?.est_chapitre}
        <Bouton
          variante="primaire"
          desactive={actionEnCours}
          onclick={() => void valider()}
        >
          ✅ Valider la version actuelle (officielle)
        </Bouton>
      {:else}
        <a class="lien-action-principal" href="#/soumission">
          📝 Soumettre un autre texte
        </a>
      {/if}
    </div>
  </header>

  {#if success}
    <Bandeau variante="succes">{success}</Bandeau>
  {/if}
  {#if erreur}
    <Bandeau variante="erreur">{erreur}</Bandeau>
  {/if}

  {#if chargement && !etat}
    <p class="chargement" role="status">Chargement de l'atelier…</p>
  {:else if !etat}
    <!-- FA3 — plus d'impasse : en cas d'échec de chargement (erreur 500, réseau…),
         l'auteur dispose d'un bouton « Réessayer » et d'un retour à l'accueil. -->
    <div class="atelier__echec-chargement">
      <Bandeau variante="erreur">
        {erreur || "Impossible de charger l'atelier — état introuvable."}
      </Bandeau>
      <div class="atelier__echec-actions">
        <Bouton variante="secondaire" onclick={() => void charger()}>
          Réessayer de charger l'atelier
        </Bouton>
        <a class="lien-retour" href="#/">Revenir à l'accueil</a>
      </div>
    </div>
  {:else if etat}
    <div class="atelier__controles">
      <OngletsPhase
        onglet={onglet}
        compteurs={etat.compteurs}
        aEmbellissement={etat.a_embellissement}
        onChangerOnglet={changerOnglet}
      />
      <ToggleMasquer
        masque={masque}
        nbMasques={etat.document.nb_masques}
        onchange={(v) => (masque = v)}
      />
    </div>

    <div class="atelier__grille">
      <div class="atelier__texte">
        <p class="info-selection">
          Sélectionnez un passage puis <strong>clic droit</strong> pour demander
          un <strong>embellissement</strong> ou une <strong>alternative</strong>.
        </p>
        <DocumentAnnote
          paragraphes={paragraphesAffiches}
          enEditionId={enEditionId}
          texteEdition={texteEdition}
          onSelectionnerGroupe={selectionnerGroupe}
          onDemanderEdition={demarrerEdition}
          onDemanderReevaluer={(p) => void reexecuterParagraphe(p)}
          onEditionChange={(t) => (texteEdition = t)}
          onValiderEdition={() => void validerEdition()}
          onAnnulerEdition={annulerEdition}
        />
      </div>
      <BarreLaterale
        corrections={etat.document.corrections_barre}
        active={correctionActive}
        onSelectionnerGroupe={selectionnerGroupe}
      />
    </div>
  {/if}
</section>

{#if menu}
  <MenuContextuel
    x={menu.x}
    y={menu.y}
    items={menu.items}
    onChoisir={appliquerActionMenu}
  />
{/if}
{#if popover}
  <PopoverSuggestion
    type={popover.type}
    texte={popover.suggestion.texte}
    explication={popover.suggestion.explication}
    alternatives={popover.suggestion.alternatives}
    erreur={popover.suggestion.erreur}
    onAppliquer={(t) => void appliquerProposition(t)}
    onAnnuler={() => (popover = null)}
  />
{/if}

<style>
  .atelier {
    display: grid;
    gap: 1.1rem;
    align-items: start;
  }
  .atelier__entete {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .atelier__titre {
    margin: 0;
    font-size: 1.5rem;
  }
  .atelier__sous-titre {
    margin: 0.2rem 0 0;
    color: var(--encre-douce);
    font-size: 0.95rem;
  }
  .atelier__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
  }
  .lien-action-principal {
    display: inline-flex;
    align-items: center;
    font: inherit;
    font-size: 0.95rem;
    line-height: 1.2;
    padding: 0.5rem 1rem;
    border-radius: var(--rayon);
    background: var(--accent);
    border: 1px solid var(--accent);
    color: #fffdf8;
    text-decoration: none;
  }
  .lien-action-principal:hover {
    background: var(--accent-fonce);
    border-color: var(--accent-fonce);
  }
  .chargement {
    color: var(--encre-douce);
    font-style: italic;
  }
  .atelier__echec-chargement {
    display: grid;
    gap: 1rem;
    justify-items: start;
  }
  .atelier__echec-actions {
    display: flex;
    align-items: center;
    gap: 1.25rem;
  }
  .atelier__echec-actions .lien-retour {
    color: var(--accent-fonce);
    font-weight: 600;
    text-decoration: none;
  }
  .atelier__echec-actions .lien-retour:hover {
    text-decoration: underline;
  }
  .info-selection {
    margin: 0 0 0.5rem;
    font-size: 0.85rem;
    color: var(--encre-douce);
  }
  .atelier__controles {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 0.5rem;
  }
  .atelier__grille {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 320px;
    gap: 1.25rem;
    align-items: start;
  }
  .atelier__texte {
    min-width: 0;
  }
  @media (max-width: 900px) {
    .atelier__grille {
      grid-template-columns: 1fr;
    }
    .atelier__controles {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>