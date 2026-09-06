"""Alertes de cohérence — v6 §6.7 : numérotation stable et double barrière /nopb.

- Numérotation : `numero_projet = COALESCE(MAX(numero_projet), 0) + 1` par projet,
  attribuée à l'insertion — ne glisse JAMAIS, même après validation d'alertes antérieures ;
- Double barrière « ne sera plus jamais re-détectée » (v6 §6.7) :
  1. les alertes `validee` sont injectées dans le prompt de la Phase 2 comme exclusions ;
  2. un post-filtre Python écarte toute re-détection dont le couple (code, cible)
     correspond à une alerte validée ;
- /nopb : statut `validee` + archivage dans le journal d'intrigue.
"""

import json

from app import db
from app.models import AlerteDetectee


async def prochain_numero(projet_id: str) -> int:
    """MAX+1 par projet (v6 §6.7) — jamais de glissement."""
    lignes = await db.interroger(
        "SELECT COALESCE(MAX(numero_projet), 0) + 1 AS suivant "
        "FROM alertes WHERE projet_id = ?",
        (projet_id,),
    )
    return int(lignes[0]["suivant"])


async def creer(projet_id: str, alerte: AlerteDetectee) -> int:
    """Insère une alerte avec son numéro stable ; retourne `numero_projet` (v6 §6.7)."""
    numero = await prochain_numero(projet_id)
    await db.executer(
        "INSERT INTO alertes (projet_id, numero_projet, niveau, code, cible, motif) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (projet_id, numero, alerte.niveau, alerte.code, alerte.cible, alerte.motif),
    )
    return numero


async def valider_choix_auteur(projet_id: str, numero: int) -> bool:
    """Équivalent /nopb (v6 §6.7) : statut `validee` + archivage au journal d'intrigue.
    Retourne False si l'alerte n'existe pas ou est déjà validée."""
    _, modifie = await db.executer(
        "UPDATE alertes SET statut = 'validee' "
        "WHERE projet_id = ? AND numero_projet = ? AND statut = 'active'",
        (projet_id, numero),
    )
    if modifie == 0:
        return False
    lignes = await db.interroger(
        "SELECT code, cible, motif FROM alertes WHERE projet_id = ? AND numero_projet = ?",
        (projet_id, numero),
    )
    ligne = lignes[0]
    await db.executer(
        "INSERT INTO journaux (projet_id, category, entity_name, data_json) "
        "VALUES (?, 'intrigue', ?, ?)",
        (
            projet_id,
            ligne["cible"] or None,
            json.dumps(
                {
                    "type": "choix_auteur",
                    "numero_alerte": numero,
                    "code": ligne["code"],
                    "motif": ligne["motif"],
                },
                ensure_ascii=False,
            ),
        ),
    )
    return True


async def exclusions_validees(projet_id: str) -> list[dict]:
    """Barrière 1 (v6 §6.7) : alertes validées, injectées au prompt comme exclusions."""
    return await db.interroger(
        "SELECT code, cible FROM alertes WHERE projet_id = ? AND statut = 'validee'",
        (projet_id,),
    )


def filtrer_redetections(
    detectees: list[AlerteDetectee], validees: list[dict]
) -> list[AlerteDetectee]:
    """Barrière 2 (v6 §6.7) : post-filtre Python écartant toute re-détection
    dont le couple (code, cible) correspond à une alerte validée."""
    exclus = {(v["code"], v["cible"] or "") for v in validees}
    return [a for a in detectees if (a.code, a.cible) not in exclus]
