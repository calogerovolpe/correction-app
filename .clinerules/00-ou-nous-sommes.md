# État Actuel du Projet — Où nous en sommes

> Ce fichier est conçu pour être lu très rapidement par Cline en début de chaque session afin de comprendre l'état exact du projet sans surcharger le contexte.

---

## 📌 Synthèse Express
- **Projet** : Application web privée mono-utilisateur de correction de manuscrits (FastAPI + SQLite WAL + Jinja/HTMX/Alpine + Mistral API).
- **Statut global** : 77/77 tests automatisés au vert (`pytest`).
- **Jalon courant terminé** : **J2.4 (Rendu texte riche & fiabilisation bulle d'alternatives)**.
- **Prochain jalon à réaliser** : **J3 — Chaîne séquentielle & Codex narratif**.

---

## 🧭 Ce qui a déjà été livré et validé

1. **J0 (Socle technique)** : SQLite WAL, schéma SQL relationnel complet, gestion projet actif.
2. **J1 (Moteur métier pur)** : Normalisation stricte du texte, découpage de paragraphes, moteur de réconciliation d'offsets, déduplication Style prioritaire.
3. **J2 / J2.1 (MVP & retours)** : Pipeline asynchrone 4 phases parallèles (Forme, Style, Technique, Embellissement), fail-fast, jauge créativité, matrice dérogable.
4. **J2.2 (Atelier interactif & Fidélité Word)** : Support texte riche (gras, italique, souligné via `RunFormat`), barre latérale droite remplaçant les tooltips, suggestions d'alternatives à la demande (`POST /api/alternatives`).
5. **J2.3 (Catégorisation déclarative)** : Nettoyage strict au collage Word, choix explicite de la catégorie (Chapitre, Passage, Extrait) avec pré-remplissage $N+1$, règle du « Dernier validé gagne » sans blocage.
6. **J2.4 (Rendu & Fiabilisation)** : Rendu fidèle des styles Word d'origine (`<em>`, `<strong>`) dans les segments de texte non corrigés de E5, passage par attributs `dataset` pour immuniser les bulles contre les guillemets et apostrophes.

---

## 🎯 Prochain Jalon : J3 — Chaîne séquentielle & Codex narratif

### Objectif
Mettre en place la mémoire persistante du roman (personnages, glossaire, évolutions, chronologie) et le suivi des chapitres officiels.

### Étapes prévues :
1. **Étape 0 (Prévention & Lisibilité du code)** : Fractionner `app/routes/web.py` (> 300 lignes) avant d'y intégrer les nouveaux écrans :
   - `web.py` : Accueil et projets (E1).
   - `analyses.py` : Soumission (E3) et suivi asynchrone (E4).
   - `resultat.py` : Visualisation annotée (E5), validation et alternatives.
   - `codex.py` : Écrans E6 (Codex) et E7 (Journaux).
2. **Écritures narratives** : Backup automatique `Connection.backup()` avant validation, enregistrement dans `chapitres` (avec hash SHA-256), `codex`, `journaux`.
3. **Phase 2 LLM** : Extraction d'entités codex, alertes de cohérence narratives (avec double barrière `/nopb` anti-redétection déjà prête dans `alertes.py`), relecture-diff de remplacement.
4. **Écrans complémentaires** : Timeline des chapitres (E2), codex éditable (E6), journaux narratifs (E7).

---

## 📚 Documents de référence
- **Journal de bord complet** : `.clinerules/README.md`
- **Spécification technique détaillée** : `docs/Architecture application web — v1 (spécification consolidée).md` *(à ne lire que sur demande explicite pour des détails d'implémentation J3)*.
