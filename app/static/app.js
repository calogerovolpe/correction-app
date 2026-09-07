/* correction-app — atelier E5 (jalon J2.5) : couches superposables, sélection
   + clic droit (embellissement / alternative), choix de corrections Forme,
   réévaluation par paragraphe, navigation clavier.
   Encapsulé en IIFE : aucune variable globale. */
(() => {
  "use strict";

  const selection = { paragrapheId: "", fragment: "", contexte: "", texteParagraphe: "" };

  /* Coordonnées viewport du dernier clic droit (jalon A) : le menu et le
     popover sont en position: fixed, donc positionnés par clientX/clientY. */
  const curseur = { x: 0, y: 0 };

  const zoneAtelier = () => document.getElementById("zone-atelier");

  function afficherErreur(message) {
    const zone = zoneAtelier();
    if (!zone) return;
    const bandeau = document.createElement("div");
    bandeau.className = "bandeau bandeau--avertissement";
    bandeau.textContent = message;
    zone.prepend(bandeau);
    setTimeout(() => bandeau.remove(), 10000);
  }

  async function poster(url, donnees) {
    const zone = zoneAtelier();
    if (!zone) return false;
    try {
      const reponse = await fetch(url, {
        method: "POST",
        body: new URLSearchParams(donnees),
      });
      if (reponse.ok) {
        zone.outerHTML = await reponse.text();
        return true;
      }
      afficherErreur(`Erreur ${reponse.status} — réessayez.`);
    } catch (erreur) {
      afficherErreur("Erreur réseau : " + erreur);
    }
    return false;
  }

  /* --- Extraction de la sélection (les <del> barrés ne font pas partie du texte courant) --- */

  function noeudsTexteVisibles(plage, conteneur) {
    const marcheur = document.createTreeWalker(conteneur, NodeFilter.SHOW_TEXT, {
      acceptNode: (noeud) =>
        noeud.parentElement && noeud.parentElement.closest("del")
          ? NodeFilter.FILTER_REJECT
          : NodeFilter.FILTER_ACCEPT,
    });
    const morceaux = [];
    let noeud;
    while ((noeud = marcheur.nextNode())) {
      if (!plage.intersectsNode(noeud)) continue;
      const debut = noeud === plage.startContainer ? plage.startOffset : 0;
      const fin = noeud === plage.endContainer ? plage.endOffset : noeud.textContent.length;
      morceaux.push(noeud.textContent.slice(debut, fin));
    }
    return morceaux.join("");
  }

  function analyserSelection(evenement) {
    const doc = document.getElementById("document-texte");
    if (!doc || !doc.contains(evenement.target)) return false;
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) return false;
    const plage = sel.getRangeAt(0);
    const paragraphe =
      plage.startContainer.parentElement &&
      plage.startContainer.parentElement.closest("[data-paragraphe-id]");
    if (!paragraphe) return false;
    const fragment = noeudsTexteVisibles(plage, paragraphe).replace(/\s+/g, " ").trim();
    if (!fragment) return false;
    const avant = document.createRange();
    avant.selectNodeContents(paragraphe);
    avant.setEnd(plage.startContainer, plage.startOffset);
    const tout = document.createRange();
    tout.selectNodeContents(paragraphe);
    selection.paragrapheId = paragraphe.dataset.paragrapheId;
    selection.fragment = fragment;
    selection.texteParagraphe = noeudsTexteVisibles(tout, paragraphe);
    selection.contexte = noeudsTexteVisibles(avant, paragraphe).slice(-60);
    return true;
  }

  function fermerPopover() {
    const pop = document.getElementById("popover-action");
    if (pop) pop.hidden = true;
  }

  document.addEventListener("contextmenu", (evenement) => {
    const menu = document.getElementById("menu-contextuel");
    if (!menu) return;
    if (!analyserSelection(evenement)) {
      menu.hidden = true;
      return;
    }
    evenement.preventDefault();
    curseur.x = evenement.clientX;
    curseur.y = evenement.clientY;
    menu.hidden = false;
    /* position: fixed (jalon A) : coordonnées viewport, robustes au scroll ;
       recentrage simple pour ne jamais sortir de l'écran. */
    menu.style.left = Math.max(8, Math.min(curseur.x, window.innerWidth - (menu.offsetWidth || 240) - 12)) + "px";
    menu.style.top = Math.max(8, Math.min(curseur.y, window.innerHeight - (menu.offsetHeight || 100) - 12)) + "px";
  });

  async function demanderSuggestion(action) {
    const url = action === "embellir" ? "/api/embellir" : "/api/alternatives";
    const charge =
      action === "embellir"
        ? { fragment: selection.fragment, paragraphe_texte: selection.texteParagraphe, contexte: selection.contexte }
        : { fragment: selection.fragment, paragraphe_texte: selection.texteParagraphe };
    try {
      const reponse = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(charge),
      });
      const donnees = await reponse.json();
      if (donnees.erreur) {
        afficherErreur(donnees.erreur);
        return;
      }
      afficherPopover(action, donnees);
    } catch (erreur) {
      afficherErreur("Erreur réseau : " + erreur);
    }
  }

  function afficherPopover(action, donnees) {
    const pop = document.getElementById("popover-action");
    if (!pop) return;
    pop.innerHTML = "";
    if (action === "embellir") {
      const titre = document.createElement("p");
      titre.className = "titre-choix";
      titre.textContent = "✨ Proposition d'embellissement";
      const explication = document.createElement("p");
      explication.className = "explication";
      explication.textContent = donnees.explication || "";
      const proposition = document.createElement("p");
      proposition.className = "proposition";
      proposition.textContent = donnees.texte;
      const bouton = document.createElement("button");
      bouton.type = "button";
      bouton.className = "btn-choix-alt";
      bouton.textContent = "Appliquer l'embellissement";
      bouton.dataset.action = "appliquer-embellissement";
      bouton.dataset.texte = donnees.texte;
      const annuler = document.createElement("button");
      annuler.type = "button";
      annuler.className = "btn-choix-alt btn-revenir-original";
      annuler.textContent = "Annuler";
      annuler.dataset.action = "fermer";
      pop.append(titre, explication, proposition, bouton, annuler);
    } else {
      const titre = document.createElement("p");
      titre.className = "titre-choix";
      titre.textContent = "🔁 Alternatives proposées";
      const liste = document.createElement("ul");
      liste.className = "liste-alternatives";
      (donnees.alternatives || []).forEach((alt) => {
        const item = document.createElement("li");
        const bouton = document.createElement("button");
        bouton.type = "button";
        bouton.className = "btn-choix-alt";
        bouton.textContent = alt;
        bouton.dataset.action = "appliquer-alternative";
        bouton.dataset.texte = alt;
        item.appendChild(bouton);
        liste.appendChild(item);
      });
      if (!(donnees.alternatives || []).length) {
        const vide = document.createElement("li");
        vide.textContent = "Aucune alternative proposée.";
        liste.appendChild(vide);
      }
      pop.append(titre, liste);
    }
    pop.hidden = false;
    /* position: fixed (jalon A) : positionné au point du clic droit — avant,
       `absolute` sans left/top le laissait hors écran (fin du document).
       Mesuré une fois visible, puis recentré pour rester dans la fenêtre. */
    pop.style.left = Math.max(8, Math.min(curseur.x, window.innerWidth - (pop.offsetWidth || 340) - 12)) + "px";
    pop.style.top = Math.max(8, Math.min(curseur.y, window.innerHeight - (pop.offsetHeight || 200) - 12)) + "px";
  }

  document.addEventListener("click", async (evenement) => {
    const menu = document.getElementById("menu-contextuel");
    if (menu && !menu.hidden && !menu.contains(evenement.target)) menu.hidden = true;
    const declencheur = evenement.target.closest("[data-action]");
    if (!declencheur) return;
    const action = declencheur.dataset.action;
    const zone = zoneAtelier();
    const idAnalyse = zone ? zone.dataset.analyseId : "";
    if (action === "fermer") {
      fermerPopover();
    } else if (action === "reevaluer") {
      evenement.preventDefault();
      await poster(`/analyses/${idAnalyse}/reevaluer`, {
        paragraphe_id: declencheur.dataset.paragrapheId,
      });
    } else if (action === "embellir" || action === "alternatives") {
      evenement.preventDefault();
      if (menu) menu.hidden = true;
      await demanderSuggestion(action);
    } else if (action === "appliquer-alternative" || action === "appliquer-embellissement") {
      evenement.preventDefault();
      fermerPopover();
      await poster(`/analyses/${idAnalyse}/${action}`, {
        paragraphe_id: selection.paragrapheId,
        fragment: selection.fragment,
        contexte: selection.contexte,
        texte: declencheur.dataset.texte || "",
      });
    }
  });

  /* --- Navigation clavier entre corrections visibles (spec §8.1) ---------- */

  document.addEventListener("keydown", (evenement) => {
    if (!document.getElementById("document-texte")) return;
    if (evenement.key === "Escape") {
      fermerPopover();
      const menu = document.getElementById("menu-contextuel");
      if (menu) menu.hidden = true;
      return;
    }
    if (evenement.key !== "ArrowRight" && evenement.key !== "ArrowLeft") return;
    const cibles = Array.from(
      document.querySelectorAll("#document-texte [data-groupe]")
    ).filter((el) => el.offsetParent !== null);
    if (cibles.length === 0) return;
    const courant = document.activeElement;
    let index = cibles.indexOf(courant);
    if (index === -1) {
      index = evenement.key === "ArrowRight" ? 0 : cibles.length - 1;
    } else {
      index = (index + (evenement.key === "ArrowRight" ? 1 : -1) + cibles.length) % cibles.length;
    }
    evenement.preventDefault();
    cibles[index].focus();
    cibles[index].scrollIntoView({ block: "center", behavior: "smooth" });
    cibles[index].click(); // synchronise la barre latérale
  });

  /* --- Composant Alpine (barre latérale) ---------------------------------- */

  document.addEventListener("alpine:init", () => {
    Alpine.data("relectureApp", () => ({
      filtres: { forme: true, style: true, technique: true },
      correctionsBarre: [],
      correctionsTechniques: [],
      correctionActive: null,

      init() {
        const source = document.getElementById("donnees-corrections");
        if (!source) return;
        try {
          this.correctionsBarre = JSON.parse(source.textContent);
        } catch {
          this.correctionsBarre = [];
        }
        this.correctionsTechniques = this.correctionsBarre.filter(
          (c) => c.phase === "technique" && c.etat === "active"
        );
        const active = this.correctionsBarre.find((c) => c.etat === "active");
        if (active) this.correctionActive = active;
      },

      selectionnerCorrection(groupe) {
        const c = this.correctionsBarre.find((item) => item.groupe === groupe);
        if (c) this.correctionActive = c;
      },

      async posterChoixForme(correction, decision) {
        const zone = zoneAtelier();
        const idAnalyse = zone ? zone.dataset.analyseId : "";
        await poster(`/analyses/${idAnalyse}/choix-forme`, {
          correction_id: correction.id,
          decision,
        });
      },
    }));
  });
})();
