"""Configuration settings class"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application Configurations pulled from .env"""
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    API_BASE_URL: str
    API_SERVER: str
    ENVIRONMENT: str = "development"

    class Config:
        """Pydantic class for telling it to load .env"""
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

ENVIRONMENT = settings.ENVIRONMENT.lower()
IS_PRODUCTION = ENVIRONMENT == "production"
IS_DEVELOPMENT = ENVIRONMENT == "development"
IS_STAGING = ENVIRONMENT == "staging"

STATIC_DIR = "app/static/dist" if IS_PRODUCTION else "app/static"

__all__ = ["settings", "ENVIRONMENT",
           "IS_PRODUCTION", "IS_DEVELOPMENT", "IS_STAGING", "STATIC_DIR"]
