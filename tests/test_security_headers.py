"""Every response carries the security headers."""
from core import security_headers


def test_html_and_api_responses_have_the_headers(client):
    for path in ("/login", "/api/budgets/"):
        response = client.get(path)
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "same-origin"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_csp_only_allows_this_site(client):
    csp = client.get("/login").headers["Content-Security-Policy"]
    directives = dict(part.strip().split(" ", 1) for part in csp.split(";") if part.strip())

    assert directives["default-src"] == "'self'"
    assert directives["object-src"] == "'none'"
    assert directives["base-uri"] == "'self'"
    assert directives["form-action"] == "'self'"
    for name, value in directives.items():
        assert "http:" not in value and "https:" not in value and "*" not in value, name


def test_hsts_only_in_production(monkeypatch):
    monkeypatch.setattr(security_headers, "IS_PRODUCTION", True)
    assert "Strict-Transport-Security" in security_headers.build_headers()

    monkeypatch.setattr(security_headers, "IS_PRODUCTION", False)
    assert "Strict-Transport-Security" not in security_headers.build_headers()
