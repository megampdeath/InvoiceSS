from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    APP_BASE_URL: str = "http://localhost:8000"
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    BACKEND_BASE_URL: str = "http://localhost:8000"

    DATABASE_URL: str = "sqlite:///./invoice_saas.db"
    DIRECT_DATABASE_URL: str | None = None
    REDIS_URL: str | None = None

    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None
    SUPABASE_SECRET_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_JWT_ISSUER: str | None = None
    SUPABASE_JWT_AUDIENCE: str = "authenticated"
    SUPABASE_STORAGE_ORIGINALS_BUCKET: str = "invoice-originals"
    SUPABASE_STORAGE_EXPORTS_BUCKET: str = "invoice-exports"
    SUPABASE_STORAGE_OCR_RAW_BUCKET: str = "ocr-raw-results"

    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_DIR: str = "./storage"

    EXTRACTION_PROVIDER: str = "mock"
    OCR_PROVIDER_API_KEY: str | None = None
    MINDEE_API_KEY: str | None = None
    AWS_REGION: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    GOOGLE_DOCUMENT_AI_PROJECT_ID: str | None = None
    GOOGLE_DOCUMENT_AI_LOCATION: str | None = None
    GOOGLE_DOCUMENT_AI_PROCESSOR_ID: str | None = None
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: str | None = None
    AZURE_DOCUMENT_INTELLIGENCE_KEY: str | None = None

    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PRICE_STARTER_MONTHLY: str | None = None
    STRIPE_PRICE_PRO_MONTHLY: str | None = None
    STRIPE_PRICE_BUSINESS_MONTHLY: str | None = None

    DEMO_USER_ID: str = "00000000-0000-4000-8000-000000000001"
    DEMO_ORGANIZATION_ID: str = "00000000-0000-4000-8000-000000000101"
    DEMO_USER_EMAIL: str = "demo@example.com"

    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024
    MAX_UPLOAD_PAGES: int = 50
    PREVIEW_TOKEN_SECRET: str = "development-preview-secret"

    @property
    def local_storage_path(self) -> Path:
        return Path(self.LOCAL_STORAGE_DIR).resolve()

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() in {"development", "dev", "local", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()

