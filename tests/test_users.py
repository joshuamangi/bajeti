import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_update_user_success(auth_headers):
    """Test updating user profile successfully"""
    update_data = {
        "first_name": "UpdatedFirst",
        "last_name": "UpdatedLast",
        "email": "updated@example.com"
    }

    response = client.put(
        "/api/users/me", json=update_data, headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["first_name"] == update_data["first_name"]
    assert data["last_name"] == update_data["last_name"]
    assert data["email"] == update_data["email"]


def test_update_user_partial(auth_headers):
    """Test updating only some user fields"""
    update_data = {
        "first_name": "PartialUpdate"
    }

    response = client.put(
        "/api/users/me", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "PartialUpdate"


def test_update_user_duplicate_email(auth_headers, create_second_user):
    """Test updating to an existing email"""
    second_user = create_second_user
    update_data = {
        "email": second_user["email"]
    }

    response = client.put(
        "/api/users/me", json=update_data, headers=auth_headers)
    assert response.status_code == 409
    assert "Email already exists" in response.json()["detail"]


def test_update_user_unauthorized():
    """Test updating user without authentication"""
    update_data = {"first_name": "Test"}
    response = client.put("/api/users/me", json=update_data)
    assert response.status_code == 401


def test_update_user_security_answer(auth_headers):
    """Test updating security answer"""
    update_data = {
        "security_answer": "NewSecurityAnswer"
    }

    response = client.put(
        "/api/users/me", json=update_data, headers=auth_headers)
    assert response.status_code == 200


def test_reset_password_success(create_user_with_security):
    """Test successful password reset"""
    user_data = create_user_with_security
    reset_data = {
        "email": user_data["email"],
        "security_answer": "TestSecurityAnswer",
        "new_password": "NewSecurePassword123"
    }

    response = client.post("/api/users/password/reset", json=reset_data)
    assert response.status_code == 200
    assert "Password reset successful" in response.json()["message"]


def test_reset_password_user_not_found():
    """Test password reset for non-existent user"""
    reset_data = {
        "email": "nonexistent@example.com",
        "security_answer": "AnyAnswer",
        "new_password": "NewPassword123"
    }

    response = client.post("/api/users/password/reset", json=reset_data)
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_reset_password_wrong_security_answer(create_user_with_security):
    """Test password reset with wrong security answer"""
    user_data = create_user_with_security
    reset_data = {
        "email": user_data["email"],
        "security_answer": "WrongAnswer",
        "new_password": "NewPassword123"
    }

    response = client.post("/api/users/password/reset", json=reset_data)
    assert response.status_code == 400
    assert "Incorrect answer" in response.json()["detail"]


def test_reset_password_no_security_answer(create_user):
    """Test password reset for user without security answer"""
    user_data = create_user
    reset_data = {
        "email": user_data["email"],
        "security_answer": "AnyAnswer",
        "new_password": "NewPassword123"
    }

    response = client.post("/api/users/password/reset", json=reset_data)
    assert response.status_code == 400
    assert "Security answer not configured" in response.json()["detail"]


# Fixtures
@pytest.fixture
def auth_headers(create_user_and_login):
    return create_user_and_login


@pytest.fixture
def create_user_and_login():
    """Create a user and login to get auth token"""
    import uuid
    unique_email = f"user_test_{uuid.uuid4().hex[:8]}@example.com"

    user_data = {
        "first_name": "Test",
        "last_name": "User",
        "email": unique_email,
        "password": "testpass123",
        "security_answer": "TestSecurityAnswer"
    }
    client.post("/api/auth/", json=user_data)

    login_data = {
        "username": unique_email,
        "password": "testpass123"
    }
    login_response = client.post("/api/auth/token", data=login_data)
    token = login_response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def create_user():
    """Create a test user without security answer"""
    import uuid
    user_data = {
        "first_name": "Test",
        "last_name": "User",
        "email": f"no_security_{uuid.uuid4().hex[:8]}@example.com",
        "password": "testpass123",
        "security_answer": ""  # Empty security answer
    }
    response = client.post("/api/auth/", json=user_data)
    return response.json()


@pytest.fixture
def create_user_with_security():
    """Create a test user with security answer"""
    import uuid
    user_data = {
        "first_name": "Security",
        "last_name": "User",
        "email": f"with_security_{uuid.uuid4().hex[:8]}@example.com",
        "password": "testpass123",
        "security_answer": "TestSecurityAnswer"
    }
    response = client.post("/api/auth/", json=user_data)
    return response.json()


@pytest.fixture
def create_second_user():
    """Create a second test user for duplicate email test"""
    import uuid
    user_data = {
        "first_name": "Second",
        "last_name": "User",
        "email": f"second_{uuid.uuid4().hex[:8]}@example.com",
        "password": "testpass123",
        "security_answer": "TestAnswer"
    }
    response = client.post("/api/auth/", json=user_data)
    return response.json()
