"""
TechSift AI - Application Configuration & Environment Settings.
Zero-cost, local-first configuration with Pydantic Settings.
"""

from pathlib import Path
from typing import List, Set
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "TechSift AI"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # File Upload Limits & Storage
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    ALLOWED_EXTENSIONS: str = "pdf,txt,md"
    STORAGE_DIR: Path = Path("./storage")
    DOCUMENTS_DIR: Path = Path("./storage/documents")
    AUDIO_DIR: Path = Path("./storage/audio")

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./techsift.db"

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL.startswith("sqlite:///"):
            return self.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
        return self.DATABASE_URL

    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL.startswith("sqlite+aiosqlite:///"):
            return self.DATABASE_URL.replace("sqlite+aiosqlite:///", "sqlite:///")
        return self.DATABASE_URL

    # AI Configuration (Free-Tier Google Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_TIMEOUT_SECONDS: float = 60.0
    GEMINI_MAX_RPM: int = 10  # Safely below free-tier 15 RPM limit
    GEMINI_MAX_RETRIES: int = 1  # Bounded retry count for transient failures (1 retry = 2 total attempts)
    GEMINI_INITIAL_BACKOFF_SECONDS: float = 2.0  # Initial delay before transient retry
    GEMINI_BACKOFF_FACTOR: float = 2.0  # Exponential multiplier for retries

    # Audio / TTS Configuration
    AUDIO_PROVIDER: str = "edge-tts"  # "edge-tts" (primary neural), "piper" (local onnx), "local" (pyttsx3/os say)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        # Guarantee common local development origins to prevent localhost vs 127.0.0.1 CORS rejections
        local_dev_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        for dev_origin in local_dev_origins:
            if dev_origin not in origins:
                origins.append(dev_origin)
        return origins

    @property
    def allowed_extensions_set(self) -> Set[str]:
        return {ext.strip().lower().lstrip(".") for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()}

    @property
    def fallback_models_list(self) -> List[str]:
        return ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-latest"]


settings = Settings()
# Ensure local storage directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
settings.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
