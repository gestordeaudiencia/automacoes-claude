from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    llm_provider: Literal["openai", "anthropic"] = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    whatsapp_driver: Literal["avisaapi", "evolution", "zapi"] = "avisaapi"
    whatsapp_api_url: str = ""
    whatsapp_api_token: str = ""

    kiwify_webhook_secret: str = ""

    email_provider: Literal["resend", "smtp", "none"] = "none"
    resend_api_key: str = ""
    email_from: str = ""

    agent_name: str = "Laura"
    agent_owner: str = "Matheus"
    company_name: str = "Coeso Capital"

    product_a_name: str = "Investidor Coeso"
    product_a_link: str = ""
    product_b_name: str = "Mentoria O Caminho"
    product_b_link: str = ""

    support_whatsapp_url: str = ""
    club_url: str = ""

    app_port: int = 8000
    app_env: Literal["development", "production"] = "production"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
