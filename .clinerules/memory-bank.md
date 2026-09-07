# Memory Bank — règles de méthode (OBLIGATOIRES pour chaque session Cline)

## 1. Lecture obligatoire en début de session

Au début de CHAQUE session, lire OBLIGATOIREMENT **tous** les fichiers de `memory-bank/` AVANT de modifier du code ou d'exécuter des commandes :

`memory-bank/projectbrief.md` · `productContext.md` · `activeContext.md` · `systemPatterns.md` · `techContext.md` · `progress.md`

## 2. Mise à jour après chaque jalon

Après chaque jalon important ou changement significatif (code + tests verts + commit + push), mettre à jour la Memory Bank — au minimum `activeContext.md` et `progress.md` (statut, contenu livré, décisions, prochain jalon).

## 3. Commande « update memory bank »

Quand l'auteur dit **« update memory bank »** : relire TOUS les fichiers de `memory-bank/` et les mettre à jour de façon cohérente (dates, état, décisions).

## 4. Source de vérité unique

La **Memory Bank est LA source de vérité** pour l'état du projet, le contexte de travail et les décisions. La spécification détaillée vit dans `docs/Architecture application web — v1 (spécification consolidée).md` (source de vérité de la *spécification*, committée avec le code) — deux rôles disjoints, aucune duplication entre eux.

Toute documentation **hors** `memory-bank/` doit POINTER vers elle, jamais la dupliquer. En cas de divergence entre la Memory Bank et un autre document : corriger avant de continuer.

## 5. Gestion du contexte

Si la fenêtre de contexte dépasse **~50-60 %**, proposer un passage de relais (résumé de l'état + prochaines étapes) avant de continuer.