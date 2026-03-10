from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # 기본 설정
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "your-secret-key"
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://192.168.219.112:3000",
    ]
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = [
        "Content-Type",
        "Authorization",
        "X-CSRF-Token",
        "Idempotency-Key",
        "X-Test-Now",
    ]
    AUTH_SUCCESS_URL: str = "http://localhost:3000"

    # 데이터베이스
    DATABASE_URL: str = "sqlite+aiosqlite:///./gcs_lms.db"
    DEV_DATABASE_URL: str = "sqlite+aiosqlite:///./gcs_lms_dev.db"
    TEST_DATABASE_URL: Optional[str] = None

    # Database Pool
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_PRE_PING: bool = True

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_CONF_URL: str = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )
    GOOGLE_CLIENT_SCOPE: str = "openid email profile"

    # Test Auth Bypass (test environment only)
    TEST_AUTH_BYPASS_ENABLED: bool = False
    TEST_AUTH_BYPASS_EMAIL: str = "test@example.com"
    TEST_AUTH_BYPASS_NAME: str = "Test User"

    # Rate Limits
    LOGIN_LIMIT: str = "5/minute"
    ME_LIMIT: str = "20/minute"
    TERMS_LIMIT: str = "60/minute"
    CONSENTS_LIMIT: str = "10/minute"
    PROTECTED_LIMIT: str = "10/minute"
    COMMENTS_WRITE_LIMIT: str = "20/minute"
    SNIPPET_WRITE_LIMIT: str = "20/minute"
    SNIPPET_ORGANIZE_LIMIT: str = "5/minute"
    TOKENS_LIST_LIMIT: str = "30/minute"
    TOKENS_WRITE_LIMIT: str = "20/minute"
    TEAMS_WRITE_LIMIT: str = "20/minute"
    USERS_LEAGUE_UPDATE_LIMIT: str = "10/minute"
    MCP_HTTP_STREAM_LIMIT: str = "30/minute"
    MCP_HTTP_MESSAGES_LIMIT: str = "120/minute"
    NOTIFICATIONS_WRITE_LIMIT: str = "30/minute"
    NOTIFICATIONS_SSE_LIMIT: str = "60/minute"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
