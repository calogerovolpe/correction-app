"""E2E réel Mistral — jalon J2.5 (environnement de données isolé : APP_DATA_DIR=data_e2e).

Depuis le jalon F2, la soumission et le suivi passent par l'API JSON `/api/v1`
(`POST /api/v1/projets`, `GET /api/v1/soumission`, `POST /api/v1/analyses`,
polling `GET /api/v1/analyses/{id}`) ; les étapes atelier (nouvelle version,
validation officielle) restent sur les routes Jinja2 E5 (consommées jusqu'à F3).

Scénario : soumission d'un chapitre → analyse 3 phases → nouvelle version
(texte courant repris) → validation officielle (chapitres + hash + backup).
Usage : .venv\\Scripts\\python scripts\\e2e_j25.py
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import urllib.request

os.environ["APP_DATA_DIR"] = "data_e2e"
BASE = "http://127.0.0.1:8124"
TEXTE = (
    "1 : La veille au matin\n\n"
    "Les sentinelles monte la garde sur les remparts, ils veillent depuis la nuit tombée.\n\n"
    "Au loin, la mer etend son voile gris jusqu a l horizon."
)


def post(url, donnees=None, json_body=None):
    if json_body is not None:
        requete = urllib.request.Request(
            BASE + url, data=json.dumps(json_body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
    else:
        corps = urllib.parse.urlencode(donnees or {}).encode("utf-8")
        requete = urllib.request.Request(BASE + url, data=corps, method="POST")
    reponse = urllib.request.urlopen(requete, timeout=180)
    return reponse.status, reponse.url, reponse.read().decode("utf-8", "replace")


def get(url):
    return urllib.request.urlopen(BASE + url, timeout=60).read().decode("utf-8", "replace")


def get_json(url):
    with urllib.request.urlopen(BASE + url, timeout=60) as reponse:
        return json.loads(reponse.read().decode("utf-8", "replace"))


def attendre(identifiant, delai=180):
    limite = time.time() + delai
    while time.time() < limite:
        page = get(f"/analyses/{identifiant}")
        if "Résultat de l'analyse" in page:
            return "terminee", page
        if "échouée" in page or "refusée" in page:
            return "echec", page
        time.sleep(3)
    return "timeout", ""


def attendre_api(identifiant, delai=180):
    """Polling ÉTApe E4 branché sur l'API JSON /api/v1 (jalon F2)."""
    limite = time.time() + delai
    while time.time() < limite:
        donnees = get_json(f"/api/v1/analyses/{identifiant}")
        statut = donnees["statut"]
        if statut in ("terminee", "echec", "rejetee"):
            return donnees
        time.sleep(3)
    return {"statut": "timeout"}


def main() -> int:
    serveur = subprocess.Popen(
        [".venv\\Scripts\\python.exe", "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", "8124"],
        cwd=os.getcwd(),
    )
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(BASE + "/", timeout=2)
                break
            except Exception:
                time.sleep(0.5)

        print("1. POST /api/v1/projets :", post("/api/v1/projets", json_body={"titre": "E2E J2.5 F2"})[0])
        prep = get_json("/api/v1/soumission")
        print("   E3 préparé : numéro attendu", prep["numero_attendu"], f"| max {prep['max_caracteres']} car.")

        statut, _, corps_post = post("/api/v1/analyses", json_body={
            "texte": TEXTE, "categorie": "chapitre", "numero_chapitre": 1,
            "phases": {"forme": True, "style": True, "technique": True},
        })
        suivi = json.loads(corps_post)
        print("2. POST /api/v1/analyses ->", statut, "| id :", suivi["id"])
        etat = attendre_api(suivi["id"])
        print("3. Analyse 1 (suivi E4 /api/v1) :", etat["statut"])
        if etat["statut"] != "terminee":
            print(etat.get("erreur") or etat)
            return 1
        print("   résultat :", etat["resultat"])
        page = get(f"/analyses/{suivi['id']}")
        print("   corrections visibles :", "ins--forme" in page, "| marque style :", "mark-style" in page)

        statut, url, _ = post(f"/analyses/{suivi['id']}/nouvelle-version")
        print("4. Nouvelle version ->", statut, url)
        identifiant2 = int(url.rsplit("/", 1)[-1])
        etat, page = attendre(identifiant2)
        print("5. Analyse 2 :", etat)
        if etat != "terminee":
            print(page[:1500])
            return 1

        statut, _, _ = post(f"/analyses/{identifiant2}/valider")
        print("6. Validation ->", statut)
        conn = sqlite3.connect(os.path.join("data_e2e", "database.sqlite3"))
        try:
            chapitre = conn.execute("SELECT numero, texte, hash FROM chapitres").fetchone()
            projet = conn.execute("SELECT current_chapter_num, chain_status FROM projets").fetchone()
        finally:
            conn.close()
        print("7. chapitres :", chapitre[0], repr(chapitre[1][:80]))
        print("   projets :", projet)
        backups = os.listdir(os.path.join("data_e2e", "backups"))
        print("8. backups :", backups)
        ok = (
            chapitre is not None
            and "monte" in chapitre[1]  # la correction réelle dépend du modèle
            and projet == (1, "ok")
            and len(backups) == 1
        )
        print("E2E :", "OK" if ok else "À VÉRIFIER MANUELLEMENT")
        return 0 if ok else 2
    finally:
        serveur.terminate()
        try:
            serveur.wait(timeout=10)
        except subprocess.TimeoutExpired:
            serveur.kill()


if __name__ == "__main__":
    sys.exit(main())
