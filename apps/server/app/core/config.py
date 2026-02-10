from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 기본 설정
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "your-secret-key"
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    AUTH_SUCCESS_URL: str = "http://localhost:3000"

    # 데이터베이스
    DATABASE_URL: str = "sqlite+aiosqlite:///./gcs_lms.db"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_CONF_URL: str = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )
    GOOGLE_CLIENT_SCOPE: str = "openid email profile"

    # Rate Limits
    LOGIN_LIMIT: str = "5/minute"
    ME_LIMIT: str = "20/minute"
    TERMS_LIMIT: str = "20/minute"
    CONSENTS_LIMIT: str = "10/minute"
    PROTECTED_LIMIT: str = "10/minute"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
