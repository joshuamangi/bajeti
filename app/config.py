"""Configuration settings class"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application COnfigurations pulled from .env"""
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    API_BASE_URL: str

    class Config:
        """Pydantic class for telling it to load .env"""
        env_file = ".env"


settings = Settings()
