# Commandes, tests et boucle de validation

## Environnement
- venv : `.venv\` à la racine du projet (déjà créé, Python 3.14.3)
- Tous les exemples ci-dessous se lancent depuis la racine du projet :
  `c:\Users\calog\OneDrive\Bureau\correction\Application web\correction-app`

## Commandes de référence (PowerShell)
```powershell
# Tests (OBLIGATOIRE avant tout commit — 85 verts attendus)
.venv\Scripts\python -m pytest -q

# Lancer le serveur de dev
.venv\Scripts\python -m uvicorn app.main:app --reload
# → http://localhost:8000

# Test de connexion LLM (ping fail-fast des 5 modèles Mistral, coût négligeable)
.venv\Scripts\python scripts\tester_llm.py

# Docker (parité dev/prod)
Copy-Item .env.example .env   # si absent — la vraie clé est dans .env existant
docker compose up --build
```

## Boucle de validation d'un jalon (MÉTHODE OBLIGATOIRE)
1. **Mode Plan d'abord** : présenter le plan du jalon à l'auteur, attendre son feu vert ;
2. Coder par petites étapes (fichiers < ~6000 caractères par édition) ;
3. **`pytest` : 100 % verts** — sinon corriger avant toute autre chose ;
4. **Test E2E réel** quand le jalon touche le pipeline LLM : lancer uvicorn (port 8124),
   soumettre un texte test via `curl.exe`, vérifier le HTML de résultat, arrêter le serveur ;
5. Mettre à jour **`.clinerules/README.md`** (statut du jalon, décisions, prochain jalon) ;
6. `git add -A` + commit (`Jn — <contenu> — N tests verts`) + `git push`.

## Règles sur les tests
- **Toute correction de bug = un test de régression** (ex. : `test_redirection_identifiant_incremental`).
- Tests unitaires pour le métier pur (aucune fixture DB), tests d'intégration via le
  `client` fixture (TestClient) + `MockLLM` injecté par `monkeypatch`.
- Fixtures clés (`tests/conftest.py`) : `dossier_donnees` (base isolée en tmp),
  `base_donnees`, `connexion` (SQL direct), `client` (TestClient).
- Attendre la fin d'un job dans les tests : polling HTTP via `_attendre()` (jamais
  d'accès DB direct concurrent pendant que le job tourne).
- Aucun test ne doit appeler la vraie API Mistral (coût + non-déterminisme) ;
  le mock suffit. E2E réel = exception manuelle, hors pytest.
