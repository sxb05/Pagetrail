from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str | None = Field(default=None)
    DATABASE_HOST: str | None = None
    DATABASE_PORT: str | None = None
    DATABASE_NAME: str | None = None
    DATABASE_USERNAME: str | None = None
    DATABASE_PASSWORD: str | None = None

    @model_validator(mode="after")
    def validate_database_settings(self) -> "Settings":
        if self.DATABASE_URL:
            return self
        required_legacy_fields = (
            "DATABASE_HOST",
            "DATABASE_PORT",
            "DATABASE_NAME",
            "DATABASE_USERNAME",
            "DATABASE_PASSWORD",
        )
        missing_fields = [
            field_name for field_name in required_legacy_fields if not getattr(self, field_name)
        ]
        if missing_fields:
            raise ValueError(
                "Set DATABASE_URL or provide all legacy database settings: "
                + ", ".join(required_legacy_fields)
            )
        return self

    class Config:
        env_file = ".env"


settings = Settings()