import hashlib
import secrets

import pytest
from pydantic import ValidationError

from app.config import LEAKED_SECRET_KEY_HASHES, Settings, secret_key_problems


def make_settings(secret_key, environment):
    return Settings(
        SECRET_KEY=secret_key,
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        API_BASE_URL="http://localhost:8000/api",
        API_SERVER="http://localhost:8000",
        ENVIRONMENT=environment,
        _env_file=None,
    )


def test_production_rejects_short_key():
    with pytest.raises(ValidationError, match="shorter than"):
        make_settings("short-key", "production")


def test_production_rejects_empty_key():
    with pytest.raises(ValidationError):
        make_settings("", "production")


def test_production_accepts_random_key():
    settings = make_settings(secrets.token_hex(32), "production")
    assert settings.ENVIRONMENT == "production"


def test_development_allows_short_key():
    settings = make_settings("short-key", "development")
    assert settings.SECRET_KEY == "short-key"


def test_known_leaked_hash_is_flagged(monkeypatch):
    """Use a throwaway value registered as leaked, so no real key is in the repo."""
    fake_leaked = secrets.token_hex(32)
    digest = hashlib.sha256(fake_leaked.encode()).hexdigest()
    monkeypatch.setattr("app.config.LEAKED_SECRET_KEY_HASHES",
                        LEAKED_SECRET_KEY_HASHES | {digest})

    assert any("known-leaked" in p for p in secret_key_problems(fake_leaked))
    with pytest.raises(ValidationError, match="known-leaked"):
        make_settings(fake_leaked, "production")
    # outside production it only warns
    assert make_settings(fake_leaked, "development").SECRET_KEY == fake_leaked
