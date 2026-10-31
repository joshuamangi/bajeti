"""In-memory limits on failed logins, password resets and phone-token captures.

Why in memory: the app runs as one uvicorn process on one Pi, so a dict is enough, needs no
new dependency and no extra service. The counters reset when the app restarts, which is an
accepted trade-off for a household app. If the app ever runs several workers, replace the
storage here (the rest of the code only calls the functions below).

Keys combine the client address with the email, so a stranger who guesses one email from
their own address cannot lock the owner out from theirs. A second, larger limit per address
stops one address from trying many emails.
"""
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

from fastapi import HTTPException, Request, status

LOGIN_WINDOW = 15 * 60
LOGIN_PER_EMAIL = 5
LOGIN_PER_IP = 30
RESET_WINDOW = 60 * 60
RESET_PER_EMAIL = 5
RESET_PER_IP = 20
TOKEN_WINDOW = 15 * 60
TOKEN_FAILS_PER_IP = 20
CAPTURE_WINDOW = 60 * 60
CAPTURES_PER_TOKEN = 60


class FailureLimiter:
    """Sliding window of failure times per key."""

    def __init__(self, max_failures: int, window_seconds: int):
        self.max_failures = max_failures
        self.window = window_seconds
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> Deque[float]:
        events = self._events[key]
        while events and now - events[0] >= self.window:
            events.popleft()
        if not events:
            self._events.pop(key, None)
            return deque()
        return events

    def retry_after(self, key: str) -> int:
        """Seconds until another attempt is allowed; 0 if the key is not blocked."""
        now = time.monotonic()
        with self._lock:
            events = self._prune(key, now)
            if len(events) < self.max_failures:
                return 0
            return max(1, int(self.window - (now - events[0])) + 1)

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._events[key].append(time.monotonic())

    def clear(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


_login_email = FailureLimiter(LOGIN_PER_EMAIL, LOGIN_WINDOW)
_login_ip = FailureLimiter(LOGIN_PER_IP, LOGIN_WINDOW)
_reset_email = FailureLimiter(RESET_PER_EMAIL, RESET_WINDOW)
_reset_ip = FailureLimiter(RESET_PER_IP, RESET_WINDOW)
_token_ip = FailureLimiter(TOKEN_FAILS_PER_IP, TOKEN_WINDOW)
# Counts every capture, not only failures: a leaked phone token cannot flood the inbox.
_capture_token = FailureLimiter(CAPTURES_PER_TOKEN, CAPTURE_WINDOW)


def reset_all() -> None:
    """Empty every counter (used by tests)."""
    for limiter in (_login_email, _login_ip, _reset_email, _reset_ip, _token_ip, _capture_token):
        limiter.reset()


def client_ip(request: Request) -> str:
    """Address of the real client.

    Cloudflare sets CF-Connecting-IP and the app port is reachable only through the tunnel
    (bound to loopback), so the header cannot be supplied by a stranger. The web pages call
    this API from the same host and forward the header, otherwise every request would look
    like it comes from the server itself.
    """
    forwarded = request.headers.get("cf-connecting-ip")
    if forwarded:
        return forwarded.strip()
    return request.client.host if request.client else "unknown"


def _email_key(ip: str, email: str) -> str:
    return f"{ip}|{email.strip().casefold()}"


def _too_many(seconds: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many attempts. Please wait a few minutes and try again.",
        headers={"Retry-After": str(seconds)},
    )


def _check(email_limiter: FailureLimiter, ip_limiter: FailureLimiter, ip: str, email: str) -> None:
    wait = max(email_limiter.retry_after(_email_key(ip, email)), ip_limiter.retry_after(ip))
    if wait:
        raise _too_many(wait)


def _fail(email_limiter: FailureLimiter, ip_limiter: FailureLimiter, ip: str, email: str) -> None:
    email_limiter.record_failure(_email_key(ip, email))
    ip_limiter.record_failure(ip)


def check_login(ip: str, email: str) -> None:
    _check(_login_email, _login_ip, ip, email)


def login_failed(ip: str, email: str) -> None:
    _fail(_login_email, _login_ip, ip, email)


def login_succeeded(ip: str, email: str) -> None:
    _login_email.clear(_email_key(ip, email))


def check_reset(ip: str, email: str) -> None:
    _check(_reset_email, _reset_ip, ip, email)


def reset_failed(ip: str, email: str) -> None:
    _fail(_reset_email, _reset_ip, ip, email)


def reset_succeeded(ip: str, email: str) -> None:
    _reset_email.clear(_email_key(ip, email))


def check_api_token(ip: str) -> None:
    wait = _token_ip.retry_after(ip)
    if wait:
        raise _too_many(wait)


def api_token_failed(ip: str) -> None:
    _token_ip.record_failure(ip)


def check_capture(token_id: int) -> None:
    """Allow one more capture for this phone token, or raise 429."""
    key = str(token_id)
    wait = _capture_token.retry_after(key)
    if wait:
        raise _too_many(wait)
    _capture_token.record_failure(key)


__all__ = [
    "client_ip", "check_login", "login_failed", "login_succeeded",
    "check_reset", "reset_failed", "reset_succeeded", "reset_all",
    "check_api_token", "api_token_failed", "check_capture",
]
