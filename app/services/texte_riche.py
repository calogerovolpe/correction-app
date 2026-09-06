"""Gestion du texte riche et découpage des styles (Word-fidèle) — Jalon J2.2.

Règles :
1. Chaque ligne de Word (ou dialogue, ou bloc) = un paragraphe indépendant (p-1, p-2...).
2. Format riche : liste de `ParagrapheRiche`, composé de `RunFormat` (texte + gras/italique/souligné).
3. Extraction en texte brut : reconstruction par concaténation des runs pour les LLM.
4. Recousage / Splicing des runs par rapport aux offsets de corrections.
"""

import json
import re
from app.models import RunFormat, ParagrapheRiche
from app.services.normalisation import Paragraphe


def extraire_texte_brut_paragraphe(p_riche: ParagrapheRiche) -> str:
    """Reconstitue le texte brut d'un paragraphe riche en concaténant ses runs."""
    return "".join(run.texte for run in p_riche.runs)


def parser_document_riche(donnees_json_ou_texte: str) -> list[ParagrapheRiche]:
    """Parse une chaîne JSON représentant une liste de ParagrapheRiche,
    ou convertit un texte brut legacy (une ligne = un paragraphe) en texte riche par défaut.
    Applique un nettoyage systématique :
    - Élimine les paragraphes vides ou composés exclusivement d'espaces/sauts de ligne.
    - Élimine les runs vides ou de purs sauts de ligne isolés en bordure.
    - Renumérote les paragraphes de manière séquentielle propre (p-1, p-2...).
    """
    if not donnees_json_ou_texte.strip():
        return []

    bruts: list[ParagrapheRiche] = []

    # Tente de parser en JSON (format v2)
    try:
        obj = json.loads(donnees_json_ou_texte)
        if isinstance(obj, list) and all("id" in p and "runs" in p for p in obj):
            bruts = [ParagrapheRiche.model_validate(p) for p in obj]
    except (json.JSONDecodeError, Exception):
        pass

    if not bruts:
        # Mode legacy ou texte brut Word : chaque ligne non vide = un paragraphe (Word-fidèle)
        lignes = [l.strip() for l in donnees_json_ou_texte.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        lignes_propres = [l for l in lignes if l]
        for i, ligne in enumerate(lignes_propres, start=1):
            bruts.append(
                ParagrapheRiche(
                    id=f"p-{i}",
                    runs=[RunFormat(texte=ligne, gras=False, italique=False, souligne=False)]
                )
            )

    # Nettoyage et normalisation défensive
    resultats: list[ParagrapheRiche] = []
    p_num = 1
    for p in bruts:
        # Nettoyer les runs
        runs_propres: list[RunFormat] = []
        for r in p.runs:
            t = r.texte.replace("\r\n", "\n").replace("\r", "\n")
            if t:
                runs_propres.append(
                    RunFormat(
                        texte=t,
                        gras=bool(r.gras),
                        italique=bool(r.italique),
                        souligne=bool(r.souligne),
                    )
                )

        texte_total = "".join(r.texte for r in runs_propres).strip()
        # On ne conserve que les paragraphes ayant un contenu textuel réel (pas de purs espaces/newlines)
        if texte_total:
            resultats.append(
                ParagrapheRiche(
                    id=f"p-{p_num}",
                    runs=runs_propres,
                )
            )
            p_num += 1

    return resultats


def serialiser_document_riche(paragraphes: list[ParagrapheRiche]) -> str:
    """Sérialise les paragraphes riches en JSON."""
    return json.dumps([p.model_dump() for p in paragraphes], ensure_ascii=False)


def convertir_en_paragraphes_simples(paragraphes_riches: list[ParagrapheRiche]) -> list[Paragraphe]:
    """Convertit la liste de ParagrapheRiche en liste de Paragraphe (texte brut) pour les LLM."""
    return [
        Paragraphe(id=p.id, texte=extraire_texte_brut_paragraphe(p))
        for p in paragraphes_riches
    ]


def decouper_runs_par_intervalle(runs: list[RunFormat], debut: int, fin: int) -> tuple[list[RunFormat], list[RunFormat], list[RunFormat]]:
    """Découpe une séquence de runs en trois parties selon un intervalle de caractères [debut, fin) :
    (runs_avant, runs_dans_intervalle, runs_apres).
    Préserve strictement le formatage (gras, italique, souligné) de chaque tronçon."""
    runs_avant: list[RunFormat] = []
    runs_milieu: list[RunFormat] = []
    runs_apres: list[RunFormat] = []

    pos = 0
    for r in runs:
        r_len = len(r.texte)
        r_debut = pos
        r_fin = pos + r_len
        pos = r_fin

        # Cas 1 : run entièrement avant l'intervalle
        if r_fin <= debut:
            runs_avant.append(r)
        # Cas 2 : run entièrement après l'intervalle
        elif r_debut >= fin:
            runs_apres.append(r)
        # Cas 3 : run chevauche ou contient l'intervalle
        else:
            # Partie avant ?
            if r_debut < debut:
                runs_avant.append(
                    RunFormat(
                        texte=r.texte[:debut - r_debut],
                        gras=r.gras,
                        italique=r.italique,
                        souligne=r.souligne
                    )
                )

            # Partie milieu
            m_debut = max(0, debut - r_debut)
            m_fin = min(r_len, fin - r_debut)
            if m_debut < m_fin:
                runs_milieu.append(
                    RunFormat(
                        texte=r.texte[m_debut:m_fin],
                        gras=r.gras,
                        italique=r.italique,
                        souligne=r.souligne
                    )
                )

            # Partie après
            if r_fin > fin:
                runs_apres.append(
                    RunFormat(
                        texte=r.texte[fin - r_debut:],
                        gras=r.gras,
                        italique=r.italique,
                        souligne=r.souligne
                    )
                )

    return runs_avant, runs_milieu, runs_apres


def extraire_mots_frequents(texte_complet: str, limite: int = 50) -> list[str]:
    """Extrait les mots les plus fréquents d'un texte littéraire (hors mots-outils courts)
    pour alimenter la consigne anti-répétition lors de la génération d'alternatives à la demande."""
    mots = re.findall(r"\b[a-zA-ZÀ-ÿ]{4,}\b", texte_complet.lower())
    mots_outils = {
        "dans", "pour", "avec", "sans", "sous", "mais", "donc", "cette", "comme", "leur",
        "plus", "tout", "tous", "toutes", "faire", "fait", "elle", "elles", "vous", "nous",
        "bien", "aussi", "encore", "alors", "après", "avant", "quand", "depuis", "vers"
    }
    compteur: dict[str, int] = {}
    for m in mots:
        if m not in mots_outils:
            compteur[m] = compteur.get(m, 0) + 1

    tries = sorted(compteur.items(), key=lambda item: item[1], reverse=True)
    return [mot for mot, freq in tries[:limite]]
