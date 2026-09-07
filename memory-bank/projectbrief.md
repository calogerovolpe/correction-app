# Brief projet — correction-app

> Source de vérité du scope. Dernière mise à jour : 2026-09-07 (jalon J2.5).

## Identité

- **Nom** : correction-app — Application web de correction de manuscrit.
- **Nature** : application web **privée, mono-utilisateur**, dédiée à la relecture d'un manuscrit unique (roman).
- **Propriétaire et unique utilisateur** : l'auteur lui-même (non développeur) — voir `productContext.md`.

## Exigences fondateurs

1. **Bibliothèque de manuscrit** : chapitres officiels, textes soumis et historiques d'analyses stockés en base — plus de copier-coller à chaque usage.
2. **Correction multi-phase** : Forme, Style, Technique — exécution parallèle, déduplication Style prioritaire.
3. **Atelier interactif (J2.5)** : le texte affiché à l'écran EST la version de travail (état courant matérialisé) ; corrections Forme appliquées par défaut et refusables ; corrections superposables en couches (Forme rouge, Style bleu, Technique fond jaune) ; Embellissement et alternatives à la demande par **sélection + clic droit** ; « Valider la version actuelle » enregistre le texte affiché.
4. **Codex vivant (J3)** : fiches, alias et journaux narratifs persistants, consultables **et éditables** dans l'UI.
5. **Chaîne N+1 visible** : timeline des chapitres officiels ; rupture → reclassement automatique en Extrait, jamais de blocage.
6. **UI de relecture sur mesure** : annotations colorées WCAG AA, panneau latéral, filtres, navigation clavier, fidélité Word (gras/italique/souligné).
7. **Local-first** : tout tourne en local ; mise en ligne seulement au jalon J5.

## Catégories de texte (métier)

**Chapitre** (numéro, chaîne N+1 stricte) / **Passage** / **Extrait** — choix explicite de l'utilisateur depuis J2.3 ; rupture de chaîne → Extrait automatique.

## Hors périmètre (v1)

- Multi-utilisateur / multi-romans simultanés (un seul projet actif à la fois).
- Éditeur de texte intégré (l'auteur écrit ailleurs ; l'application corrige).
- Chunking de textes longs (refusé par l'auteur) — seul `max_caracteres` (30 000) s'applique.
- Synchronisation cloud, mobile, hors-ligne, facturation, quotas, télémétrie.

## Décisions arbitérées par l'auteur (NE PAS RÉOUVRIR)

- **A4 — Fournisseur Mistral uniquement** par clé API (`mistral-small-latest` pour les phases) — aucun LLM local.
- **J2.5 — Atelier v2** (voir `progress.md` et spec §11, décisions 27-32) :
  - **Validation du texte affiché** : « Valider la version actuelle » (Chapitres, avec confirmation) enregistre EXACTEMENT le texte à l'écran, corrigé ou non ; Passage/Extrait → « Soumettre un autre texte » avec les dernières configurations pré-cochées ;
  - **Embellissement à la demande** : plus une phase de soumission (jauge de E3 supprimée) ; sélection + clic droit → réécriture contextualisée puis réévaluation des corrections du paragraphe ;
  - **Alternatives à la demande** : sélection + clic droit (synonyme, champ lexical cohérent avec le contexte) — fin des bulles au clic gauche ;
  - **Couches superposables** : Forme = rouge barré/inséré, Style = soulignement pointillé bleu, Technique = fond jaune — les chevauchements s'affichent tous ;
  - **Backup natif SQLite** avant toute écriture dans `chapitres` (rotation `APP_BACKUPS_MAX`).
- **Matrice de phases = pré-sélection dérogable** (J2.1) : cases pré-cochées selon la catégorie, l'utilisateur décoche/coche librement.
- **Refusés** : chunking des textes, échappement backticks du manuscrit, toggle d'affichage du texte complet (paragraphes non corrigés masqués avec compteur).
- **Chaîne** : rupture → reclassement automatique en Extrait (jamais de blocage) ; N=N sans remplacement → Extrait ; remplacement officiel explicite (case à cocher).
- **Option B** : panne de phase en cours d'analyse → arrêt global, aucun résultat partiel, aucune écriture narrative.
- **Déploiement final** : local d'abord ; J5 = Docker + Caddy (TLS) + auth simple sur le VPS, option Tailscale documentée.

## Spécification détaillée

Le détail complet (métier + applicatif + registre des décisions) vit dans **`docs/Architecture application web — v1 (spécification consolidée).md`** — source de vérité de la *spécification*, versionnée avec le code (toute évolution y est committée dans le même commit que le code concerné). Ce fichier n'en duplique que l'essentiel du scope.