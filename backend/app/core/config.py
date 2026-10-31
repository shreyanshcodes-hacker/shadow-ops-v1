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

    # Database Configuration (Supabase PostgreSQL / Google Cloud SQL)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    DIRECT_URL: Optional[str] = None
    SUPABASE_URL: str = "https://placeholder.supabase.co"
    SUPABASE_ANON_KEY: str = "placeholder-anon-key"
    SUPABASE_SERVICE_ROLE_KEY: str = "placeholder-service-role-key"
    SUPABASE_JWT_SECRET: Optional[str] = None

    # Google Cloud SQL Configuration
    USE_CLOUD_SQL_CONNECTOR: bool = False
    CLOUD_SQL_CONNECTION_NAME: Optional[str] = None
    CLOUD_SQL_DATABASE: str = "shadowops"
    CLOUD_SQL_USER: Optional[str] = None
    CLOUD_SQL_PASSWORD: Optional[str] = None
    CLOUD_SQL_IAM_AUTH: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Firebase Authentication
    FIREBASE_PROJECT_ID: str = "shadow-ops-6957d"
    FIREBASE_CLIENT_EMAIL: Optional[str] = None
    FIREBASE_PRIVATE_KEY: Optional[str] = None

    # AI Providers & Controls
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-flash-lite-latest"
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
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,https://shadow-ops-v1.vercel.app"

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
        origins = []
        if self.FRONTEND_URL:
            origins.append(self.FRONTEND_URL.strip().rstrip("/"))
        if self.CORS_ORIGINS:
            for origin in self.CORS_ORIGINS.split(","):
                clean = origin.strip().rstrip("/")
                if clean and clean not in origins:
                    origins.append(clean)
        # Always guarantee deployed Vercel frontend is an authorized origin
        production_origin = "https://shadow-ops-v1.vercel.app"
        if production_origin not in origins:
            origins.append(production_origin)
        return origins or ["http://localhost:3000"]


settings = Settings()
