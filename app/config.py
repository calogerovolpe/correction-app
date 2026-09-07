"""Paramètres applicatifs (cahier des charges §4.3, équivalent des Valves v6 §2.2).

Les clés API vivent exclusivement dans .env (jamais commité) — décision A5.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
    )

    # Chemins
    data_dir: Path = Path("data")

    # Couche LLM (compatible OpenAI) — Mistral par clé API uniquement (décision A4)
    llm_base_url: str = "https://api.mistral.ai/v1"
    llm_api_key: str = ""

    # Modèles par phase (2 à 6) — vide = non configuré
    modele_phase2: str = ""
    modele_forme: str = ""
    modele_style: str = ""
    modele_technique: str = ""
    modele_embellissement: str = ""

    # Garde-fous et timeouts (v6 §2.2)
    max_caracteres: int = 30000
    timeout_phase: int = 90
    timeout_ping: int = 10
    retries_ping: int = 1
    backups_max: int = 20
    mode_debug: bool = False

    # Températures par phase (v6 §2.2) : correction 0.0, embellissement 0.8
    temperature_correction: float = 0.0
    temperature_embellissement: float = 0.8

    # Variante linguistique : france | quebec | belgique
    variante: str = "france"


settings = Settings()
