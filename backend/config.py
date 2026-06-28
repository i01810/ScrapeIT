"""
AskAI backend configuration.

Primary source: backend/.env
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- SQL Server ---
    db_server: str = "localhost"
    db_name: str = "YourDB"
    db_user: str = "username"
    db_password: str = "password"
    db_driver: str = "ODBC Driver 17 for SQL Server"
    db_trust_server_certificate: bool = True

    # Optional: comma-separated allowlist (empty = use askai_rules/synonyms.yaml allowlist)
    db_include_tables: str = ""

    # --- Local LLM via Ollama ---
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5-coder:1.5b"
    ollama_temperature: float = 0.0

    # --- API server ---
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    # --- SQL chain ---
    max_query_rows: int = 200
    askai_verbose: bool = True

    @property
    def sqlalchemy_uri(self) -> str:
        from urllib.parse import quote_plus

        # Named instances (SERVER=HOST\INSTANCE) fail in host-style URLs; pass full ODBC string.
        odbc_connect = quote_plus(self.pyodbc_connection_string)
        return f"mssql+pyodbc:///?odbc_connect={odbc_connect}"

    @property
    def pyodbc_connection_string(self) -> str:
        trust = "yes" if self.db_trust_server_certificate else "no"
        return (
            f"DRIVER={{{self.db_driver}}};"
            f"SERVER={self.db_server};"
            f"DATABASE={self.db_name};"
            f"UID={self.db_user};"
            f"PWD={self.db_password};"
            f"TrustServerCertificate={trust};"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def db_configured(self) -> bool:
        return self.db_user not in {"", "username"} and self.db_password not in {"", "password"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
