"""Application configuration loaded from environment variables / .env."""
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "PocketSmart AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # --- Security ---
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # --- Gemini ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS: int = 45

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./pocketsmart.db"

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    # --- Uploads ---
    MAX_IMAGE_SIZE_MB: int = 5
    ALLOWED_IMAGE_TYPES: str = "image/png,image/jpeg,image/jpg,image/webp"

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_exist(cls, v: str) -> str:
        if not v or len(v) < 16:
            raise ValueError(
                "SECRET_KEY is missing or too short. Set a long random string in .env "
                "(see .env.example)."
            )
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_image_types(self) -> set[str]:
        return {t.strip().lower() for t in self.ALLOWED_IMAGE_TYPES.split(",") if t.strip()}

    @property
    def max_image_size_bytes(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024

    @property
    def gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
