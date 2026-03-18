"""
Config — Todo desde .env, nunca hardcodeado.
"""
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # General
    env: Literal["development", "production"] = "development"
    secret_key: str = "change-me-in-production"

    # Stripe
    stripe_secret_key: str = "sk_test_REPLACE_WITH_YOUR_KEY"
    stripe_webhook_secret: str = "whsec_REPLACE_WITH_YOUR_WEBHOOK_SECRET"
    stripe_pro_monthly_price_id: str = "price_REPLACE_MONTHLY"
    stripe_pro_yearly_price_id: str = "price_REPLACE_YEARLY"

    # License settings
    license_duration_days: int = 30          # días que dura una licencia mensual
    demo_license_key: str = "PISKU-PRO-DEMO-1234"  # key de demo válida

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # URLs
    success_url: str = "http://localhost:8000/success.html"
    cancel_url: str = "http://localhost:8000/#pricing"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
