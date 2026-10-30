from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Service & Networking
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    PORT: int = 8000

    # Supabase PostgreSQL & API
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    DIRECT_URL: Optional[str] = None
    SUPABASE_URL: str = "https://placeholder.supabase.co"
    SUPABASE_ANON_KEY: str = "placeholder-anon-key"
    SUPABASE_SERVICE_ROLE_KEY: str = "placeholder-service-role-key"
    SUPABASE_JWT_SECRET: Optional[str] = None

    # Firebase Authentication
    FIREBASE_PROJECT_ID: str = "shadow-ops-6957d"
    FIREBASE_CLIENT_EMAIL: Optional[str] = None
    FIREBASE_PRIVATE_KEY: Optional[str] = None

    # AI Providers & Controls
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GROK_API_KEY: Optional[str] = None
    GROK_MODEL: str = "grok-beta"
    AI_MAX_FINDINGS_PER_RUN: int = 25
    AI_MAX_INPUT_CHARS: int = 12000
    AI_REQUEST_TIMEOUT_SECONDS: int = 25
    AI_MAX_RETRIES: int = 1
    AI_COST_CAP_PER_RUN_USD: float = 2.0
    AI_PROMPT_VERSION: str = "v1.0"

    # Security & CORS
    SECRET_KEY: str = "temporary-secret-key-for-development-change-in-production-32chars"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Background Workers & Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # n8n Automation
    N8N_WEBHOOK_URL: Optional[str] = None
    N8N_HMAC_SECRET: Optional[str] = None

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT.lower() == "test"

    @property
    def parsed_cors_origins(self) -> List[str]:
        if self.is_production:
            return [self.FRONTEND_URL]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
