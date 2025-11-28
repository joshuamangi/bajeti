import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

from main import app

client = TestClient(app)


class TestCategories:
    def test_get_all_categories_success(self, auth_headers):
        """Test getting all categories for authenticated user"""
        response = client.get("/api/categories/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_all_categories_unauthorized(self):
        """Test getting categories without authentication"""
        response = client.get("/api/categories/")
        assert response.status_code == 401

    def test_create_category_success(self, auth_headers):
        """Test creating a new category"""
        category_data = {
            "name": "Groceries",
            "limit_amount": 500.0
        }

        response = client.post(
            "/api/categories/", json=category_data, headers=auth_headers)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == category_data["name"]
        assert data["limit_amount"] == category_data["limit_amount"]
        assert "id" in data
        assert "user_id" in data

    def test_create_category_unauthorized(self):
        """Test creating category without authentication"""
        category_data = {"name": "Groceries", "limit_amount": 500.0}
        response = client.post("/api/categories/", json=category_data)
        assert response.status_code == 401

    def test_get_category_by_id_success(self, auth_headers, create_category):
        """Test getting a specific category"""
        category = create_category
        response = client.get(
            f"/api/categories/{category['id']}", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == category["id"]
        assert data["name"] == category["name"]

    def test_get_category_by_id_not_found(self, auth_headers):
        """Test getting non-existent category"""
        response = client.get("/api/categories/999", headers=auth_headers)
        assert response.status_code == 404
        assert "Category not found" in response.json()["detail"]

    def test_get_category_by_id_unauthorized(self, create_category):
        """Test getting category without auth"""
        category = create_category
        response = client.get(f"/api/categories/{category['id']}")
        assert response.status_code == 401

    def test_update_category_success(self, auth_headers, create_category):
        """Test updating a category"""
        category = create_category
        update_data = {
            "name": "Updated Groceries",
            "limit_amount": 600.0
        }

        response = client.put(
            f"/api/categories/{category['id']}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["limit_amount"] == update_data["limit_amount"]

    def test_update_category_not_found(self, auth_headers):
        """Test updating non-existent category"""
        update_data = {"name": "Test", "limit_amount": 100.0}
        response = client.put("/api/categories/999",
                              json=update_data, headers=auth_headers)
        assert response.status_code == 404

    def test_delete_category_success(self, auth_headers, create_category):
        """Test deleting a category"""
        category = create_category
        response = client.delete(
            f"/api/categories/{category['id']}", headers=auth_headers)
        assert response.status_code == 204

    def test_delete_category_not_found(self, auth_headers):
        """Test deleting non-existent category"""
        response = client.delete("/api/categories/999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_categories_with_stats_success(self, auth_headers):
        """Test getting categories with expense stats"""
        response = client.get(
            "/api/categories/with-stats", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            category = data[0]
            assert "id" in category
            assert "name" in category
            assert "expense_count" in category
            assert "balance" in category
            assert "expenses" in category

    def test_get_categories_with_stats_unauthorized(self):
        """Test getting stats without authentication"""
        response = client.get("/api/categories/with-stats")
        assert response.status_code == 401


# Fixtures for test data
@pytest.fixture
def auth_headers(create_user_and_login):
    """Get authentication headers"""
    return create_user_and_login


@pytest.fixture
def create_user_and_login():
    """Create a user and login to get auth token"""
    # Create user
    user_data = {
        "first_name": "Category",
        "last_name": "Test",
        "email": "category_test@example.com",
        "password": "testpass123",
        "security_answer": "TestAnswer"
    }
    client.post("/api/auth/", json=user_data)

    # Login
    login_data = {
        "username": "category_test@example.com",
        "password": "testpass123"
    }
    login_response = client.post("/api/auth/token", data=login_data)
    token = login_response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def create_category(auth_headers):
    """Create a test category"""
    import uuid
    category_data = {
        "name": f"Test Category {uuid.uuid4().hex[:8]}",  # Make unique
        "limit_amount": 300.0
    }
    response = client.post(
        "/api/categories/", json=category_data, headers=auth_headers)
    return response.json()
