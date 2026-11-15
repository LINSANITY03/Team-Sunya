
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application metadata
    APP_NAME: str = "Crop Rotation API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Dataset configuration
    DATA_DIR: Path = Path("data/Crop/cleaned")

    # API configuration
    API_V1_PREFIX: str = "/api/v1"

    # Rotation defaults
    DEFAULT_TOP_K: int = Field(default=5, ge=1, le=100)
    DEFAULT_SEASON_DAYS: int = Field(default=365, gt=0)
    MAX_ROTATION_CANDIDATES: int = Field(default=1000, ge=1)

    # CORS configuration
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()


settings = get_settings()
