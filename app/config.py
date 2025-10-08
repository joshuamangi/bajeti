"""Configuration settings class"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application Configurations pulled from .env"""
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    API_BASE_URL: str
    API_SERVER: str

    class Config:
        """Pydantic class for telling it to load .env"""
        env_file = ".env"


settings = Settings()
