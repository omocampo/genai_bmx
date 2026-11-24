from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración centralizada y tipada de la aplicación."""

    # Google Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-4-hydrogen"
    gemini_embedding_model: str = "gemini-embedding-001"

    # PostgreSQL + pgvector
    postgres_user: str = "banamex_user"
    postgres_password: str = "banamex_pass"
    postgres_db: str = "banamex_ai"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Servidor FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def postgres_psycopg_uri(self) -> str:
        """URI estándar para psycopg3 y LangGraph Checkpointer."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_sqlalchemy_uri(self) -> str:
        """URI con driver psycopg3 para langchain-postgres (PGVectorStore)."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Retorna una instancia cacheada de la configuración."""
    return Settings()


settings = get_settings()

