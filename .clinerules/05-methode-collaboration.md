# Méthode de collaboration avec l'auteur

## Profil du propriétaire
- **Auteur de roman**, non développeur. Il arbitre les décisions métier, teste dans le
  navigateur, et fait des retours concrets (ex. J2.1 : « impossible de tester mon texte »,
  « pré-cochez les cases », « ajoutez une jauge de créativité »).
- Ses retours sont des **bugs ou des demandes de fonctionnalité légitimes** : toujours les
  prendre au sérieux, diagnostiquer la cause racine (logs serveur, base SQLite), corriger,
  et couvrir par un test de régression.

## Cycle de travail d'une session
1. **Lire ce dossier `.clinerules` en entier** (surtout README.md = journal de bord).
2. Vérifier l'état : `git log --oneline -5`, `pytest -q` (doivent être verts).
3. **Mode Plan** : proposer le plan du jalon/correctif, attendre la validation.
4. Exécuter selon la boucle de validation (03-commandes-et-tests.md).
5. Terminer par : tests verts → mise à jour README.md → commit → push → résumé clair
   en français à l'auteur (ce qui a été fait, comment tester, prochaine étape).

## Règles de communication
- Réponses en **français**, pédagogues, sans jargon non expliqué.
- Toujours expliquer une correction de bug : cause racine → fix → test → prévention.
- Donner à l'auteur des instructions **copier-coller** pour tester lui-même (URL, commandes).
- Le serveur de dev peut être lancé en arrière-plan pour lui (`Start-Process` uvicorn port 8000) ;
  lui indiquer le PID et comment l'arrêter.

## Décisions d'architecture déjà arbitrees par l'auteur (NE PAS RÉOUVRIR)
1. Fournisseur **Mistral uniquement** par clé API — pas de LLM local (A4).
2. **Matrice de phases = pré-sélection dérogable** (J2.1) : l'UI pré-coche selon la catégorie,
   l'utilisateur décoche/coche librement.
3. **Jauge de créativité** : température Embellissement choisie par analyse (0 → 1.5).
4. Refusés par l'auteur : chunking des textes, échappement backticks du manuscrit,
   toggle d'affichage du texte complet (les paragraphes non corrigés restent masqués avec compteur).
5. Rupture de chaîne → **reclassement automatique en Extrait** (jamais de blocage) ;
   N=N sans remplacement explicite → Extrait ; remplacement officiel = case à cocher (=/maj).
6. Option B sur panne de phase en cours d'analyse (arrêt global, aucun résultat partiel).
7. Déploiement final : local d'abord, J5 = Docker + Caddy (TLS) + auth simple sur le VPS,
   option Tailscale documentée.

## Historique des jalons restants
Voir `.clinerules/README.md` (journal de bord, mis à jour à chaque jalon) — le détail du
prochain jalon (contenu + critères d'acceptation) y est spécifié.
