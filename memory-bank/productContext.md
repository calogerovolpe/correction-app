# Contexte produit — pourquoi ce projet existe

> Dernière mise à jour : 2026-09-07.

## Origine et problème résolu

- L'auteur relit et corrige son manuscrit de roman chapitre par chapitre ; la correction manuelle est lente, peu cohérente et ne garde **aucune mémoire du roman** (personnages, glossaire, chronologie).
- **Genèse** : le métier a d'abord été spécifié comme une fonction OpenWebUI (archives « Architecture fonction correction de texte » v3 → v6, hors repo, dossier grand-parent — jamais développée). Les contraintes de plateforme ont été écartées ; le métier a été transposé en application web autonome (cahier des charges initial → spec consolidée v1).

## Ce que le produit fait (parcours nominal)

1. L'auteur colle un texte (Chapitre / Passage / Extrait) dans un éditeur qui respecte la mise en forme Word (gras, italique, souligné, paragraphes) — nettoyage strict au collage.
2. Un **ping fail-fast** vérifie la disponibilité des modèles Mistral AVANT toute consommation de tokens.
3. Les phases cochées (Forme, Style, Technique, Embellissement) s'exécutent **en parallèle** (jobs asynchrones suivis par HTMX).
4. Le résultat s'affiche en **document annoté interactif** : couleurs WCAG AA, panneau latéral, bulles d'alternatives à la demande, bascule Original/Corrigé.
5. L'auteur valide la version ou soumet une nouvelle version ; les écritures narratives (chapitres, codex, journaux) seront réservées à la validation officielle (J3).

## Expérience visée

- **Zéro surprise** : jamais de résultat partiel ; une panne se voit immédiatement (statut `echec` explicite, jamais de statut fantôme).
- **Fidélité au texte** : espaces et sauts de ligne conservés, formatage Word restitué.
- **Contrôle de l'auteur** : « dernier validé gagne », choix d'auteur sur les alertes, matrice dérogable, jauge de créativité.
- **Confidentialité** : le manuscrit ne quitte jamais la machine, sauf les requêtes Mistral nécessaires aux analyses.
- Aucun jargon ; instructions copier-coller pour tester.

## Utilisateur cible

Unique : **l'auteur, non développeur**. Il arbitre les décisions métier, teste dans le navigateur, et fait des retours concrets (ex. J2.1) qui deviennent des bugs à corriger + tests de régression.