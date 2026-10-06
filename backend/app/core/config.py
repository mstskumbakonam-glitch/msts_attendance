"""
Application Configuration (pydantic-settings)
Loaded once via lru_cache; validates environment before startup.
"""
from functools import lru_cache
from typing import List
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Smart Attendance & Security System"
    app_version: str = "0.1.0"
    app_env: str = "development"  # development | staging | production
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smart_attendance"
    sync_database_url: str = ""

    # Security
    secret_key: str = "CHANGE_ME"
    jwt_secret: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    jwt_expire_minutes: int = 30
    login_rate_limit: str = "5/minute"

    @property
    def token_secret(self) -> str:
        return self.jwt_secret if self.jwt_secret else self.secret_key

    # CORS — comma-separated list in env, parsed to list
    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501"

    # AI / device
    device: str = "cpu"
    onnx_provider: str = "CPUExecutionProvider"
    face_match_threshold: float = 0.50
    face_detection_confidence: float = 0.60
    deduplication_cooldown_seconds: int = 1800
    insightface_model_name: str = "buffalo_s"
    frame_sample_interval: int = 5
    default_camera_source: str = "0"
    app_timezone: str = "Asia/Kolkata"
    # RTSP
    rtsp_open_timeout_ms: int = 5000
    rtsp_reconnect_max_seconds: int = 30
    camera_1_credentials: str = ""
    camera_2_credentials: str = "" 

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Fail fast if secret_key is still CHANGE_ME in non-development environments."""
        if self.app_env != "development" and self.secret_key in ("CHANGE_ME", "change_this_to_a_secure_random_string_in_production"):
            raise ValueError(
                "SECRET_KEY must be changed from the default value before running in "
                f"'{self.app_env}' environment. Generate one with: "
                "python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
