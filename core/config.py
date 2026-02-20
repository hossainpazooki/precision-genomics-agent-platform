"""Global configuration settings for the Precision Genomics Agent Platform."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "Precision Genomics Agent Platform"
    environment: str = "local"
    debug: bool = False

    # Database (PostgreSQL + TimescaleDB)
    database_url: str = "postgresql://postgres:postgres@localhost:5432/precision_genomics"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Anthropic (LLM)
    anthropic_api_key: str | None = None

    # Data paths
    data_dir: str = "data"
    raw_data_dir: str = "data/raw"

    # ML settings
    random_state: int = 42
    cv_folds: int = 10
    n_estimators: int = 500

    # Auth
    require_auth: bool = False
    api_keys: str | None = None

    # Feature flags
    enable_feature_store: bool = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
