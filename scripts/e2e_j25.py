"""E2E réel Mistral — jalon J2.5 (environnement de données isolé : APP_DATA_DIR=data_e2e).

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

        print("1. POST /projets :", post("/projets", {"titre": "E2E J2.5"})[0])
        statut, _, _ = post("/analyses", {
            "texte": TEXTE, "categorie": "chapitre", "numero_chapitre": "1",
            "phases": json.dumps({"forme": True, "style": True, "technique": True}),
        })
        print("2. POST /analyses ->", statut)
        etat, page = attendre(1)
        print("3. Analyse 1 :", etat)
        if etat != "terminee":
            print(page[:1500])
            return 1
        print("   corrections visibles :", "ins--forme" in page, "| marque style :", "mark-style" in page)

        statut, url, _ = post("/analyses/1/nouvelle-version")
        print("4. Nouvelle version ->", statut, url)
        etat, page = attendre(2)
        print("5. Analyse 2 :", etat)
        if etat != "terminee":
            print(page[:1500])
            return 1

        statut, _, _ = post("/analyses/2/valider")
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
