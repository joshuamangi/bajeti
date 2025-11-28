from fastapi.testclient import TestClient
import pytest
from unittest.mock import Mock

from main import app

client = TestClient(app)


def test_create_user_success():
    """Test successful user creation"""
    user_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "testuser@example.com",
        "password": "securitypassword123",
        "security_answer": "Another"  # Fixed typo from 'secret_answer'
    }

    response = client.post("/api/auth/", json=user_payload)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["email"] == user_payload["email"]
    assert data["first_name"] == user_payload["first_name"]
    assert data["last_name"] == user_payload["last_name"]
    assert "created_at" in data
    assert "updated_at" in data
    # Password should not be returned
    assert "password" not in data
    assert "hashed_password" not in data


def test_create_user_duplicate_email():
    """Test creating user with duplicate email"""
    user_payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "duplicate@example.com",
        "password": "securitypassword123",
        "security_answer": "Answer"
    }

    # First creation should succeed
    response1 = client.post("/api/auth/", json=user_payload)
    assert response1.status_code == 201

    # Second creation with same email should fail
    response2 = client.post("/api/auth/", json=user_payload)
    assert response2.status_code == 400
    assert "Email already registered" in response2.json()["detail"]


def test_login_success():
    """Test successful login"""
    # First create a user
    user_payload = {
        "first_name": "Login",
        "last_name": "Test",
        "email": "login@example.com",
        "password": "testpassword123",
        "security_answer": "TestAnswer"
    }

    client.post("/api/auth/", json=user_payload)

    # Then try to login
    login_data = {
        "username": "login@example.com",
        "password": "testpassword123"
    }

    response = client.post("/api/auth/token", data=login_data)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


def test_login_wrong_password():
    """Test login with wrong password"""
    user_payload = {
        "first_name": "Login",
        "last_name": "Test",
        "email": "login2@example.com",
        "password": "testpassword123",
        "security_answer": "TestAnswer"
    }

    client.post("/api/auth/", json=user_payload)

    login_data = {
        "username": "login2@example.com",
        "password": "wrongpassword"
    }

    response = client.post("/api/auth/token", data=login_data)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_nonexistent_user():
    """Test login with non-existent user"""
    login_data = {
        "username": "nonexistent@example.com",
        "password": "anypassword"
    }

    response = client.post("/api/auth/token", data=login_data)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_get_current_user_success():
    """Test getting current user with valid token"""
    # Create user and login to get token
    user_payload = {
        "first_name": "Current",
        "last_name": "User",
        "email": "current@example.com",
        "password": "testpassword123",
        "security_answer": "TestAnswer"
    }

    client.post("/api/auth/", json=user_payload)

    login_data = {
        "username": "current@example.com",
        "password": "testpassword123"
    }

    login_response = client.post("/api/auth/token", data=login_data)
    token = login_response.json()["access_token"]

    # Use token to get current user
    response = client.get(
        "/api/auth/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "current@example.com"
    assert data["first_name"] == "Current"
    assert data["last_name"] == "User"


def test_get_current_user_invalid_token():
    """Test getting current user with invalid token"""
    response = client.get(
        "/api/auth/users/me",
        headers={"Authorization": "Bearer invalid_token"}
    )

    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]


def test_get_current_user_no_token():
    """Test getting current user without token"""
    response = client.get("/api/auth/users/me")

    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


def test_create_user_missing_fields():
    """Test creating user with missing required fields"""
    incomplete_payload = {
        "first_name": "Test",
        # Missing last_name, email, password, security_answer
    }

    response = client.post("/api/auth/", json=incomplete_payload)
    assert response.status_code == 422  # Validation error
