"""Configuration settings class"""
import hashlib
import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# 43 characters is the length of 32 random bytes encoded as urlsafe base64
# (`openssl rand -hex 32` gives 64 characters).
MIN_SECRET_KEY_LENGTH = 43

# SHA-256 hashes of keys that were exposed and must never be used again.
# Only hashes are stored here, never the keys themselves.
LEAKED_SECRET_KEY_HASHES = frozenset({
    "2dfca5cbf159a1684374ae1756f82d337994ff9a1322b987d8f4bb2d38934776",
})


def secret_key_problems(secret_key: str) -> list[str]:
    """Return the reasons a SECRET_KEY is not acceptable (empty list if fine)."""
    problems = []
    if len(secret_key) < MIN_SECRET_KEY_LENGTH:
        problems.append(
            f"SECRET_KEY is shorter than {MIN_SECRET_KEY_LENGTH} characters")
    digest = hashlib.sha256(secret_key.encode("utf-8")).hexdigest()
    if digest in LEAKED_SECRET_KEY_HASHES:
        problems.append("SECRET_KEY is a known-leaked value and must be rotated")
    return problems


class Settings(BaseSettings):
    """Application Configurations pulled from .env"""
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    API_BASE_URL: str
    API_SERVER: str
    ENVIRONMENT: str = "development"
    # Closed by default: the site is public, so strangers must not be able to create accounts.
    # Set REGISTRATION_OPEN=true only while you add a household member.
    REGISTRATION_OPEN: bool = False
    # "Today" for due dates is local time in Nairobi (UTC+3, no daylight saving).
    APP_TIMEZONE_OFFSET_HOURS: int = 3
    # Keep the original text of a captured payment after it is approved or dismissed.
    KEEP_RAW_MESSAGES: bool = False
    # iCloud link of the "Send to Bajeti" Shortcut, shown on the Account page. Production: GitHub
    # Actions variable SHORTCUT_INSTALL_URL, written into .env by deploy.yml. Never in the repo.
    SHORTCUT_INSTALL_URL: str = ""

    @model_validator(mode="after")
    def check_secret_key(self):
        """Refuse weak or leaked keys in production; warn elsewhere."""
        problems = secret_key_problems(self.SECRET_KEY)
        if not problems:
            return self
        if self.ENVIRONMENT.lower() == "production":
            raise ValueError("; ".join(problems))
        for problem in problems:
            logger.warning("%s (allowed outside production)", problem)
        return self

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
