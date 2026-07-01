from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "ShelfLife"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite:///./shelflife.db"

    # JWT (access-only)
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12h — "persistent" per BRD

    # Bootstrap admin (created by seed script if absent)
    FIRST_ADMIN_USERNAME: str = "admin"
    FIRST_ADMIN_PASSWORD: str = "admin123"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
