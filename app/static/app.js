/* correction-app — interactions clavier du document annoté (v6 §7.5).
   Encapsulé en IIFE : aucune variable globale, aucun impact hors du document. */
(() => {
  "use strict";

  const focusables = () =>
    Array.from(
      document.querySelectorAll(".ins[tabindex='0'], .sugg[tabindex='0']")
    ).filter((el) => el.offsetParent !== null);

  document.addEventListener("keydown", (evenement) => {
    if (evenement.key === "ArrowRight" || evenement.key === "ArrowLeft") {
      const liste = focusables();
      if (liste.length === 0) return;
      const courant = document.activeElement;
      let index = liste.indexOf(courant);
      if (index === -1) index = evenement.key === "ArrowRight" ? -1 : 0;
      const pas = evenement.key === "ArrowRight" ? 1 : -1;
      index = (index + pas + liste.length) % liste.length;
      evenement.preventDefault();
      liste[index].focus();
      liste[index].scrollIntoView({ block: "center", behavior: "smooth" });
    } else if (evenement.key === "Escape") {
      // Ferme le tooltip ouvert (v6 §7.5)
      if (document.activeElement && document.activeElement.blur) {
        document.activeElement.blur();
      }
    }
  });
})();
