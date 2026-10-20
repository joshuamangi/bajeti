"""Tokens do not depend on the JWT library: the format is plain HS256, so tokens issued
before the switch from python-jose to PyJWT keep working."""
import base64
import hashlib
import hmac
import json
import pathlib
import time
from datetime import timedelta

from app.config import settings
from app.utils.tokens import verify_token
from services.token_service import TokenService

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _hand_made_token(claims, key=None, alg="HS256", digest=hashlib.sha256):
    """Build a JWT with nothing but hmac, the way any library would."""
    header = _b64(json.dumps({"alg": alg, "typ": "JWT"}).encode())
    body = _b64(json.dumps(claims).encode())
    signing_input = f"{header}.{body}".encode()
    key = (key or settings.SECRET_KEY).encode()
    signature = _b64(hmac.new(key, signing_input, digest).digest())
    return f"{header}.{body}.{signature}"


def _claims(**extra):
    return {"sub": "a@example.com", "user_id": 1, "exp": int(time.time()) + 600, **extra}


def test_token_made_by_hand_is_accepted():
    payload = TokenService.decode_token(_hand_made_token(_claims(ver=3)))

    assert payload["sub"] == "a@example.com" and payload["ver"] == 3
    assert verify_token(_hand_made_token(_claims())) is not None


def test_issued_token_is_standard_hs256():
    token = TokenService.create_access_token(
        {"sub": "a@example.com", "user_id": 1}, timedelta(minutes=5))

    header, body, signature = token.split(".")
    expected = _b64(hmac.new(settings.SECRET_KEY.encode(),
                             f"{header}.{body}".encode(), hashlib.sha256).digest())
    assert signature == expected
    assert json.loads(base64.urlsafe_b64decode(header + "==")) == {"alg": "HS256", "typ": "JWT"}


def test_unsigned_token_is_rejected():
    header = _b64(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    token = f"{header}.{_b64(json.dumps(_claims()).encode())}."

    assert TokenService.decode_token(token) is None
    assert verify_token(token) is None


def test_token_signed_with_another_key_or_algorithm_is_rejected():
    assert TokenService.decode_token(_hand_made_token(_claims(), key="x" * 64)) is None
    hs512 = _hand_made_token(_claims(), alg="HS512", digest=hashlib.sha512)
    assert TokenService.decode_token(hs512) is None
    assert verify_token(hs512) is None


def test_expired_and_garbage_tokens_are_rejected():
    expired = _hand_made_token({**_claims(), "exp": int(time.time()) - 5})

    assert TokenService.decode_token(expired) is None
    assert verify_token(expired) is None
    assert TokenService.decode_token("not.a.token") is None
    assert TokenService.decode_token("") is None


def test_python_jose_is_gone():
    """python-jose has open critical advisories and no fixed release."""
    for name in ("requirements.txt", "requirements-dev.txt"):
        assert "jose" not in (ROOT / name).read_text().lower(), name
    offenders = [
        str(path.relative_to(ROOT))
        for folder in ("app", "core", "routers", "services", "tests", "data", "schema")
        for path in (ROOT / folder).rglob("*.py")
        if path.name != "test_jwt_library.py" and "jose" in path.read_text()
    ]
    assert offenders == []
