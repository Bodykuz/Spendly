"""Centralised application settings, loaded from environment."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="Spendly", alias="APP_NAME")
    app_secret_key: str = Field(default="change-me", alias="APP_SECRET_KEY")
    app_base_url: str = Field(default="http://localhost:8000", alias="APP_BASE_URL")
    app_frontend_callback_scheme: str = Field(
        default="spendly", alias="APP_FRONTEND_CALLBACK_SCHEME"
    )
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_cors_origins: str = Field(
        default="http://localhost:3000,spendly://callback", alias="APP_CORS_ORIGINS"
    )

    # JWT
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=30, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # DB
    database_url: str = Field(alias="DATABASE_URL")
    database_url_async: str = Field(default="", alias="DATABASE_URL_ASYNC")

    # Redis / Celery
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND"
    )

    # PSD2 provider
    psd2_provider: str = Field(default="gocardless", alias="PSD2_PROVIDER")
    gocardless_secret_id: str = Field(default="", alias="GOCARDLESS_SECRET_ID")
    gocardless_secret_key: str = Field(default="", alias="GOCARDLESS_SECRET_KEY")
    gocardless_base_url: str = Field(
        default="https://bankaccountdata.gocardless.com/api/v2",
        alias="GOCARDLESS_BASE_URL",
    )
    gocardless_default_country: str = Field(default="PL", alias="GOCARDLESS_DEFAULT_COUNTRY")
    gocardless_consent_days: int = Field(default=90, alias="GOCARDLESS_CONSENT_DAYS")
    gocardless_tx_history_days: int = Field(default=730, alias="GOCARDLESS_TX_HISTORY_DAYS")

    # Observability
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")

    @field_validator("app_cors_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.app_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
