from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Charge la configuration depuis les variables d'environnement (.env)."""

    # --- LLM ---
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # --- Catalogue ---
    catalog_path: Path = BASE_DIR / "data" / "catalog.json"

    # --- WhatsApp Cloud API (Meta) ---
    whatsapp_verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "change-me")
    whatsapp_access_token: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    whatsapp_phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    whatsapp_api_version: str = os.getenv("WHATSAPP_API_VERSION", "v20.0")

    # --- Entreprise (utilisé dans le prompt système) ---
    business_name: str = os.getenv("BUSINESS_NAME", "ElectroCI")
    business_description: str = os.getenv(
        "BUSINESS_DESCRIPTION",
        "distributeur de matériel électrique et de solutions d'énergie solaire "
        "pour particuliers et professionnels en Côte d'Ivoire",
    )

    @property
    def whatsapp_configured(self) -> bool:
        return bool(self.whatsapp_access_token and self.whatsapp_phone_number_id)

    @property
    def llm_configured(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
