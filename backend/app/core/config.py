from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime configuration. Values come from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Environment values such as CORS_ORIGINS are normal comma-separated text,
        # not mandatory JSON arrays. Field validators normalize them below.
        enable_decoding=False,
    )

    app_name: str = "Indian Food Nutrition API"
    app_env: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    mongodb_uri: str | None = None
    database_name: str = "indian_food_nutrition"
    jwt_secret: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    model_path: Path = PROJECT_ROOT / "ml" / "models" / "efficientnet_v2_s_indian_food.pth"
    class_names_path: Path = PROJECT_ROOT / "ml" / "class_names.json"
    model_version: str = "efficientnet-v2-s-indian-food-v1"
    model_name: str = "EfficientNetV2-S Indian Food Classifier"
    confidence_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    model_image_size: int = Field(default=384, ge=64, le=2048)

    upload_dir: Path = PROJECT_ROOT / "uploads"
    max_upload_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    model_upload_dir: Path = PROJECT_ROOT / "model_versions"
    max_model_upload_bytes: int = Field(default=600 * 1024 * 1024, gt=0)
    admin_emails: list[str] = Field(default_factory=list)
    nutrition_seed_path: Path = PROJECT_ROOT / "backend" / "data" / "platesignal_nutrition_seed.json"

    llm_provider: str = "gemini"
    llm_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash-lite"
    rag_provider: str | None = None
    rag_database: str | None = None
    firebase_project_id: str | None = None
    firebase_service_account_path: Path | None = None

    @field_validator("model_path", "class_names_path", "upload_dir", "model_upload_dir", "nutrition_seed_path", "firebase_service_account_path", mode="before")
    @classmethod
    def resolve_relative_path(cls, value: str | Path | None) -> Path | None:
        if value is None or value == "":
            return None
        path = Path(value).expanduser()
        return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("admin_emails", mode="before")
    @classmethod
    def split_admin_emails(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return [item.strip().lower() for item in value]

    @field_validator("mongodb_uri", mode="before")
    @classmethod
    def empty_database_url_is_unconfigured(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
