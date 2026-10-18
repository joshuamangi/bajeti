from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from app.handlers import target_handlers
from app.handlers.target_handlers import parse_amounts
from main import app
from services.token_service import TokenService


def make_client():
    client = TestClient(app, follow_redirects=False)
    token = TokenService.create_access_token(
        {"sub": "handler@example.com", "user_id": 1}, timedelta(minutes=5))
    client.cookies.set("access_token", token)
    return client


def toast_of(response):
    """Return (path, toast type, message) from a redirect_with_toast response."""
    assert response.status_code == 303
    url = urlparse(response.headers["location"])
    query = parse_qs(url.query)
    return url.path, query["toast"][0], query["message"][0]


class FakeApi:
    """Replaces the web layer's API calls and records what was sent."""

    def __init__(self, monkeypatch, status_code=200, json=None, error=None):
        self.calls = []
        self.status_code = status_code
        self.json = json if json is not None else {}
        self.error = error
        for name in ("save_target", "update_target", "remove_target"):
            monkeypatch.setattr(target_handlers.target_service, name, self._make(name))

    def _make(self, name):
        async def fake(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if self.error:
                raise self.error
            return httpx.Response(self.status_code, json=self.json)
        return fake


FORM = {"budget_id": 7, "category_id": 3,
        "short_term_amount": "100", "mid_term_amount": "", "long_term_amount": "2,500.50"}


class TestParseAmounts:
    def test_blank_means_none(self):
        assert parse_amounts("", "  ", None) == {
            "short_term_amount": None, "mid_term_amount": None, "long_term_amount": None}

    def test_numbers_and_thousands_separators(self):
        assert parse_amounts("100", "1,500.50", "0") == {
            "short_term_amount": "100", "mid_term_amount": "1500.50", "long_term_amount": "0"}

    @pytest.mark.parametrize("bad", ["abc", "1e", "NaN", "Infinity", "-Infinity", "1.2.3"])
    def test_rejects_non_numbers(self, bad):
        with pytest.raises(ValueError):
            parse_amounts(bad, "", "")

    def test_rejects_more_than_two_decimals(self):
        with pytest.raises(ValueError, match="two decimal"):
            parse_amounts("1.005", "", "")

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="negative"):
            parse_amounts("", "-1", "")


class TestSaveTarget:
    def test_requires_login(self):
        response = TestClient(app, follow_redirects=False).post("/dashboard/targets", data=FORM)
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    @pytest.mark.parametrize("api_status", [200, 201])
    def test_success(self, monkeypatch, api_status):
        api = FakeApi(monkeypatch, status_code=api_status)
        path, kind, message = toast_of(make_client().post("/dashboard/targets", data=FORM))
        assert (path, kind) == ("/dashboard", "success")
        name, args, _ = api.calls[0]
        assert name == "save_target"
        assert args[1:3] == (7, 3)
        assert args[3] == {"short_term_amount": "100", "mid_term_amount": None,
                           "long_term_amount": "2500.50"}

    def test_invalid_amount_never_reaches_the_api(self, monkeypatch):
        api = FakeApi(monkeypatch)
        _, kind, message = toast_of(make_client().post(
            "/dashboard/targets", data={**FORM, "short_term_amount": "abc"}))
        assert kind == "error" and "numbers" in message
        assert api.calls == []

    def test_negative_amount_never_reaches_the_api(self, monkeypatch):
        api = FakeApi(monkeypatch)
        _, kind, message = toast_of(make_client().post(
            "/dashboard/targets", data={**FORM, "mid_term_amount": "-5"}))
        assert kind == "error" and "negative" in message
        assert api.calls == []

    def test_api_type_mismatch_shows_the_reason(self, monkeypatch):
        FakeApi(monkeypatch, status_code=400,
                json={"detail": "Category type does not match budget type"})
        _, kind, message = toast_of(make_client().post("/dashboard/targets", data=FORM))
        assert kind == "error"
        assert message == "Category type does not match budget type"

    def test_api_404_is_an_error_toast(self, monkeypatch):
        FakeApi(monkeypatch, status_code=404, json={"detail": "Budget not Found"})
        _, kind, message = toast_of(make_client().post("/dashboard/targets", data=FORM))
        assert kind == "error" and "not found" in message

    def test_api_401_sends_user_to_login(self, monkeypatch):
        FakeApi(monkeypatch, status_code=401, json={"detail": "Could not validate credentials"})
        response = make_client().post("/dashboard/targets", data=FORM)
        assert response.status_code == 303
        assert response.headers["location"] == "/login"

    def test_network_error_is_an_error_toast_not_a_500(self, monkeypatch):
        FakeApi(monkeypatch, error=httpx.ConnectError("down"))
        _, kind, message = toast_of(make_client().post("/dashboard/targets", data=FORM))
        assert kind == "error" and "reach the server" in message

    def test_unexpected_api_status_is_an_error_toast(self, monkeypatch):
        FakeApi(monkeypatch, status_code=500, json={})
        _, kind, _ = toast_of(make_client().post("/dashboard/targets", data=FORM))
        assert kind == "error"


class TestEditAndDeleteTarget:
    def test_edit_success(self, monkeypatch):
        api = FakeApi(monkeypatch, status_code=200)
        response = make_client().post(
            "/dashboard/targets/7/11/edit", data={"short_term_amount": "5"})
        assert toast_of(response)[:2] == ("/dashboard", "success")
        name, args, _ = api.calls[0]
        assert name == "update_target" and args[1:3] == (7, 11)
        assert args[3] == {"short_term_amount": "5", "mid_term_amount": None,
                           "long_term_amount": None}

    def test_edit_invalid_amount(self, monkeypatch):
        api = FakeApi(monkeypatch)
        response = make_client().post(
            "/dashboard/targets/7/11/edit", data={"long_term_amount": "x"})
        assert toast_of(response)[1] == "error"
        assert api.calls == []

    def test_edit_not_found(self, monkeypatch):
        FakeApi(monkeypatch, status_code=404)
        response = make_client().post("/dashboard/targets/7/11/edit", data={})
        assert toast_of(response)[1] == "error"

    def test_delete_success(self, monkeypatch):
        api = FakeApi(monkeypatch, status_code=204)
        response = make_client().post("/dashboard/targets/7/11/delete")
        assert toast_of(response)[:2] == ("/dashboard", "success")
        assert api.calls[0][0] == "remove_target" and api.calls[0][1][1:] == (7, 11)

    def test_delete_not_found(self, monkeypatch):
        FakeApi(monkeypatch, status_code=404)
        assert toast_of(make_client().post("/dashboard/targets/7/11/delete"))[1] == "error"

    def test_requires_login(self):
        client = TestClient(app, follow_redirects=False)
        assert client.post("/dashboard/targets/7/11/edit", data={}).status_code == 302
        assert client.post("/dashboard/targets/7/11/delete").status_code == 302
