"""Security headers added to every response."""
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import IS_PRODUCTION

# The templates still use inline onclick handlers and style attributes, so 'unsafe-inline' is
# needed for scripts and styles. That weakens the XSS protection of the CSP; moving the
# handlers into the script files would let us remove it (see docs/backlog.md).
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])


def build_headers() -> dict:
    headers = {
        "Content-Security-Policy": CONTENT_SECURITY_POLICY,
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "same-origin",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }
    if IS_PRODUCTION:
        # Six months, no includeSubDomains: the hostname is served over https by Cloudflare.
        headers["Strict-Transport-Security"] = "max-age=15552000"
    return headers


class SecurityHeadersMiddleware:
    """Plain ASGI middleware, so it adds no per-request task or body buffering."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                for name, value in build_headers().items():
                    if name.lower().encode() not in present:
                        headers.append((name.lower().encode(), value.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
