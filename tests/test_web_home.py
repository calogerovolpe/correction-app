"""Tests de l'écran E1 — Accueil / Projets.

Depuis le jalon F1, la page d'accueil `/` est la SPA Svelte compilée
(`app/static/spa/index.html`) lorsqu'elle est présente sur disque (build du
frontend, gitignoré) ; sinon repli dev sur le template Jinja2 `index.html`.
Le comportement fonctionnel d'E1 (création, activation, suppression,
analyses récentes) est couvert par l'API `/api/v1` (`test_api_projets.py`)
et par les tests Vitest du frontend. Les assertions de contenu qui
dépendaient du rendu Jinja2 ont été migrées en conséquence au jalon F1.
"""

from pathlib import Path

SPA_INDEX = (
    Path(__file__).resolve().parent.parent / "app" / "static" / "spa" / "index.html"
)


def test_accueil_repond(client):
    reponse = client.get("/")
    assert reponse.status_code == 200
    if SPA_INDEX.exists():
        assert '<div id="app">' in reponse.text
    else:
        assert "Aucun projet" in reponse.text


def test_creation_jinja2_redirige_vers_accueil(client):
    # Route Jinja2 /projets conservée jusqu'à F5 : la redirection vers
    # l'accueil fonctionne toujours (le rendu de la cible dépend de la SPA).
    reponse = client.post(
        "/projets", data={"titre": "Mon roman"}, follow_redirects=False
    )
    assert reponse.status_code == 303
