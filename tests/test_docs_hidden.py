"""The interactive API docs are only served outside production."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from main import api_docs_urls


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_are_404_in_production(path):
    app = FastAPI(**api_docs_urls(is_production=True))
    assert TestClient(app).get(path).status_code == 404


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_stay_available_outside_production(path):
    app = FastAPI(**api_docs_urls(is_production=False))
    assert TestClient(app).get(path).status_code == 200
