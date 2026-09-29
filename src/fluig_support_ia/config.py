"""Configuracao central da aplicacao, carregada de variaveis de ambiente / .env."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Todas as configuracoes da aplicacao em um unico lugar."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # --- OpenAI -----------------------------------------------------------
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # --- Base de conhecimento --------------------------------------------
    database_url: str = "postgresql://fluig:fluig@localhost:5432/fluig_support"
    vector_store: Literal["in_memory", "pgvector"] = "in_memory"
    retrieval_top_k: int = 6

    # --- Fluig ------------------------------------------------------------
    fluig_base_url: str = ""
    fluig_consumer_key: str = ""
    fluig_consumer_secret: str = ""
    fluig_access_token: str = ""
    fluig_token_secret: str = ""
    fluig_timeout_seconds: float = 30.0
    fluig_read_only: bool = True

    # --- Agente -----------------------------------------------------------
    agent_max_tool_iterations: int = Field(default=6, ge=1, le=20)
    redact_pii: bool = True

    @property
    def fluig_configured(self) -> bool:
        """Indica se ha credenciais suficientes para falar com o Fluig."""
        return bool(
            self.fluig_base_url
            and self.fluig_consumer_key
            and self.fluig_consumer_secret
            and self.fluig_access_token
            and self.fluig_token_secret
        )


@lru_cache
def get_settings() -> Settings:
    """Retorna as configuracoes em cache (uma unica instancia por processo)."""
    return Settings()
