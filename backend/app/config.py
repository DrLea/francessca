"""Application configuration loaded from environment variables.

All secrets come from the environment. Nothing is hardcoded here.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Values are read from environment variables (and a local `.env` during
    development). See `.env.template` for the full list.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # JWT
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(1440, alias="JWT_EXPIRE_MINUTES")

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    # Anthropic
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-haiku-4-5-20251001", alias="ANTHROPIC_MODEL")

    # Google OAuth
    google_client_id: str = Field("", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field("", alias="GOOGLE_CLIENT_SECRET")

    # SMTP
    smtp_host: str = Field("", alias="SMTP_HOST")
    smtp_port: int = Field(587, alias="SMTP_PORT")
    smtp_user: str = Field("", alias="SMTP_USER")
    smtp_password: str = Field("", alias="SMTP_PASSWORD")
    smtp_from: str = Field("no-reply@francessca.app", alias="SMTP_FROM")

    # URLs
    frontend_url: str = Field("http://localhost:3000", alias="FRONTEND_URL")
    backend_url: str = Field("http://localhost:8000", alias="BACKEND_URL")
    cors_origins: str = Field("http://localhost:3000", alias="CORS_ORIGINS")

    # App behaviour
    free_tier_token_limit: int = Field(100_000, alias="FREE_TIER_TOKEN_LIMIT")
    admin_email: str = Field("", alias="ADMIN_EMAIL")
    admin_password: str = Field("", alias="ADMIN_PASSWORD")
    max_upload_size: int = Field(26_214_400, alias="MAX_UPLOAD_SIZE")
    upload_dir: str = Field("/data/uploads", alias="UPLOAD_DIR")

    # When true (default), the lawyer directory is seeded with a fictional
    # sample dataset on first startup so the directory/search UI works without
    # a live scrape. Set to false once real data is synced via the scraper.
    use_fake_lawyers_db: bool = Field(True, alias="USE_FAKE_LAWYERS_DB")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
