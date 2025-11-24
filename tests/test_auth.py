from fastapi.testclient import TestClient
import app
import pytest

client = TestClient(app)


def test_create_user():
    """ test creating user"""
    user_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "testuser@example.com",
        "password": "securitypaswword123",
        "secret_answer": "Another"
    }

    # create user
    response = client.post("/api/auth/", json=user_payload)
    # assert return code 200
    assert response.status_code == 201
    # asserr response returns the expected keys
    data = response.json()
    assert "id" in data
    assert data["email"] == user_payload["email"]
    assert data["first_name"] == user_payload["first_name"]
    assert data["last_name"] == user_payload["last_name"]

    assert "created_at" in data
    assert "updated_at" in data
