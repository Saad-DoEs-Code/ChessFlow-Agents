"""Central configuration. Values come from environment / .env (see .env.example).
No secrets in code. Model strings are config-driven so agents never hardcode them."""
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CFAIOS_", extra="ignore")

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "change-me"

    vector_backend: str = "pgvector"
    vector_dsn: str = ""

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"
    google_api_key: str = ""
    google_model: str = "gemini-3.1-flash-lite"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    stockfish_path: str = "/usr/bin/stockfish"
    syzygy_path: str = ""


settings = Settings()
