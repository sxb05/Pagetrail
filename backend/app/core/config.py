from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import REPO_ROOT


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # A full DATABASE_URL is sufficient. Discrete fields remain supported for
    # deployments that construct the URL from individual credentials.
    DATABASE_URL: str | None = None
    DATABASE_ADMIN_URL: str | None = None
    DATABASE_HOST: str | None = None
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str | None = None
    DATABASE_USERNAME: str | None = None
    DATABASE_PASSWORD: str | None = None

    SECRET_KEY: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # These integrations are used by individual features, not by the web
    # server's import/startup path. Missing keys should not stop port binding.
    GEMINI_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    SUPABASE_URL: str | None = None
    SUPABASE_PUBLISHABLE_KEY: str | None = None
    SUPABASE_SECRET_KEY: str | None = None
    SUPABASE_JWKS_URL: str | None = None


settings = Settings()
