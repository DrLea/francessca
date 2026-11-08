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

    # AI provider: "anthropic" for the hosted Claude API, "local" for any
    # OpenAI-compatible server — which is what the offline desktop build
    # runs (a bundled llama.cpp serving a small instruct model).
    ai_provider: str = Field("anthropic", alias="AI_PROVIDER")

    # Anthropic
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-haiku-4-5-20251001", alias="ANTHROPIC_MODEL")

    # Local model (ai_provider="local"). Base URL includes the /v1 suffix.
    local_ai_base_url: str = Field("http://127.0.0.1:8757/v1", alias="LOCAL_AI_BASE_URL")
    local_ai_model: str = Field("local", alias="LOCAL_AI_MODEL")
    # Small models on CPU are slow; this is a per-request ceiling, not a
    # target. Long jobs (document translation) are split into small calls
    # rather than leaning on this.
    local_ai_timeout: float = Field(600.0, alias="LOCAL_AI_TIMEOUT")

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
    # How many orders a newly registered lawyer can accept for free. After
    # that they see a "contact us" screen until an admin unlocks more.
    lawyer_free_orders: int = Field(3, alias="LAWYER_FREE_ORDERS")
    # Shown on that screen, and where lawyer sign-ups / feedback are mailed.
    # Falls back to ADMIN_EMAIL.
    support_email: str = Field("", alias="SUPPORT_EMAIL")
    admin_email: str = Field("", alias="ADMIN_EMAIL")
    admin_password: str = Field("", alias="ADMIN_PASSWORD")
    max_upload_size: int = Field(26_214_400, alias="MAX_UPLOAD_SIZE")
    upload_dir: str = Field("/data/uploads", alias="UPLOAD_DIR")

    # When true (default), the lawyer directory is seeded with a fictional
    # sample dataset on first startup so the directory/search UI works without
    # a live scrape. Set to false once real data is synced via the scraper.
    use_fake_lawyers_db: bool = Field(True, alias="USE_FAKE_LAWYERS_DB")

    # --- Desktop downloads offered on the landing page -----------------
    # Read at request time, not baked into the frontend bundle: publishing a
    # new release is then a config change and a backend restart, with no
    # rebuild. The SHA-256 values are optional but worth setting -- the
    # executable is unsigned, so a checksum is all a visitor has to check it
    # against.
    download_version: str = Field("", alias="DOWNLOAD_VERSION")
    # Serve the builds from this deployment instead of a third-party host.
    # Put the files in this directory under the names in DOWNLOAD_FILENAMES
    # and they are offered at /public/download/<platform> -- same domain as
    # the app, so wherever Francessca is reachable, so is the download.
    download_dir: str = Field("", alias="DOWNLOAD_DIR")
    download_windows: str = Field("", alias="DOWNLOAD_WINDOWS")
    download_windows_sha256: str = Field("", alias="DOWNLOAD_WINDOWS_SHA256")
    download_mac: str = Field("", alias="DOWNLOAD_MAC")
    download_mac_sha256: str = Field("", alias="DOWNLOAD_MAC_SHA256")
    download_linux: str = Field("", alias="DOWNLOAD_LINUX")
    download_linux_sha256: str = Field("", alias="DOWNLOAD_LINUX_SHA256")

    # --- Desktop build -------------------------------------------------
    # When set, the API also serves the exported frontend from this
    # directory, so the whole app is one process on one port.
    frontend_dist: str = Field("", alias="FRONTEND_DIST")
    # Absolute path to a bundled tesseract binary, for OCR without a
    # system-wide install.
    tesseract_cmd: str = Field("", alias="TESSERACT_CMD")
    # Directory holding DejaVuSans.ttf / DejaVuSans-Bold.ttf for PDF export.
    font_dir: str = Field("", alias="FONT_DIR")

    @property
    def contact_email(self) -> str:
        return (self.support_email or self.admin_email).strip()

    @property
    def is_local_ai(self) -> bool:
        return self.ai_provider.strip().lower() == "local"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
