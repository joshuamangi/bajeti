import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_all_expenses_success(auth_headers, create_expense):
    """Test getting all expenses for authenticated user"""
    response = client.get("/api/expenses/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_all_expenses_empty(auth_headers):
    """Test getting expenses when user has none"""
    response = client.get("/api/expenses/", headers=auth_headers)
    assert response.status_code == 404
    assert "No expenses found" in response.json()["detail"]


def test_get_all_expenses_unauthorized():
    """Test getting expenses without authentication"""
    response = client.get("/api/expenses/")
    assert response.status_code == 401


def test_get_current_month_expenses_success(auth_headers, create_expense):
    """Test getting current month expenses"""
    expense = create_expense  # This creates expense with month "2024-01"
    response = client.get(
        f"/api/expenses/by-month?month={expense['month']}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_current_month_expenses_empty(auth_headers):
    """Test getting current month expenses when none exist"""
    response = client.get("/api/expenses/month", headers=auth_headers)
    assert response.status_code == 404
    assert "No expenses found" in response.json()["detail"]


def test_get_expenses_by_month_success(auth_headers, create_expense):
    """Test getting expenses by specific month"""
    response = client.get(
        "/api/expenses/by-month?month=2024-01", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_expenses_by_month_invalid_format(auth_headers):
    """Test getting expenses with invalid month format"""
    response = client.get(
        "/api/expenses/by-month?month=invalid", headers=auth_headers)
    assert response.status_code == 422  # Validation error


def test_get_expenses_by_month_empty(auth_headers):
    """Test getting expenses for month with no data"""
    response = client.get(
        "/api/expenses/by-month?month=2023-01", headers=auth_headers)
    assert response.status_code == 404


def test_get_expenses_by_category_success(auth_headers, create_expense):
    """Test getting expenses by category"""
    expense = create_expense
    response = client.get(
        f"/api/expenses/category/{expense['category_id']}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_expenses_by_category_empty(auth_headers, create_category):
    """Test getting expenses for category with none"""
    category = create_category
    response = client.get(
        f"/api/expenses/category/{category['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_get_expenses_by_category_and_month_success(auth_headers, create_expense):
    """Test getting expenses by category and month"""
    expense = create_expense
    response = client.get(
        f"/api/expenses/by-category-month?category_id={expense['category_id']}&month={expense['month']}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_expenses_by_category_and_month_empty(auth_headers, create_category):
    """Test getting expenses for category/month with none"""
    category = create_category
    response = client.get(
        f"/api/expenses/by-category-month?category_id={category['id']}&month=2023-01",
        headers=auth_headers
    )
    assert response.status_code == 404


def test_create_expense_success(auth_headers, create_category):
    """Test creating a new expense"""
    category = create_category
    expense_data = {
        "category_id": category["id"],
        "amount": 100.50,
        "description": "Test expense",
        "month": "2024-01"
    }

    response = client.post(
        "/api/expenses/", json=expense_data, headers=auth_headers)
    assert response.status_code == 201

    data = response.json()
    assert float(data["amount"]) == expense_data["amount"]
    assert data["description"] == expense_data["description"]
    assert data["month"] == expense_data["month"]
    assert "id" in data
    assert "user_id" in data


def test_create_expense_unauthorized(create_category):
    """Test creating expense without authentication"""
    category = create_category
    expense_data = {
        "category_id": category["id"],
        "amount": 100.50,
        "description": "Test expense",
        "month": "2024-01"
    }
    response = client.post("/api/expenses/", json=expense_data)
    assert response.status_code == 401


def test_update_expense_success(auth_headers, create_expense):
    """Test updating an expense"""
    expense = create_expense
    update_data = {
        "category_id": expense["category_id"],
        "amount": 200.75,
        "description": "Updated expense",
        "month": "2024-02"
    }

    response = client.put(
        f"/api/expenses/{expense['id']}", json=update_data, headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert float(data["amount"]) == update_data["amount"]
    assert data["description"] == update_data["description"]
    assert data["month"] == update_data["month"]


def test_update_expense_not_found(auth_headers):
    """Test updating non-existent expense"""
    update_data = {
        "category_id": 1,
        "amount": 100.0,
        "description": "Test",
        "month": "2024-01"
    }
    response = client.put("/api/expenses/999",
                          json=update_data, headers=auth_headers)
    assert response.status_code == 404


def test_delete_expense_success(auth_headers, create_expense):
    """Test deleting an expense"""
    expense = create_expense
    response = client.delete(
        f"/api/expenses/{expense['id']}", headers=auth_headers)
    assert response.status_code == 204


def test_delete_expense_not_found(auth_headers):
    """Test deleting non-existent expense"""
    response = client.delete("/api/expenses/999", headers=auth_headers)
    assert response.status_code == 404


# Fixtures
@pytest.fixture
def auth_headers(create_user_and_login):
    return create_user_and_login


@pytest.fixture
def create_user_and_login():
    """Create a user and login to get auth token"""
    import uuid
    unique_email = f"expense_test_{uuid.uuid4().hex[:8]}@example.com"

    user_data = {
        "first_name": "Expense",
        "last_name": "Test",
        "email": unique_email,
        "password": "testpass123",
        "security_answer": "TestAnswer"
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
def create_category(auth_headers):
    """Create a test category"""
    import uuid
    category_data = {
        "name": f"Test Category {uuid.uuid4().hex[:8]}",
        "limit_amount": 500.0
    }
    response = client.post(
        "/api/categories/", json=category_data, headers=auth_headers)
    return response.json()


@pytest.fixture
def create_expense(auth_headers, create_category):
    """Create a test expense"""
    category = create_category
    expense_data = {
        "category_id": category["id"],
        "amount": 150.25,
        "description": "Test expense description",
        "month": "2024-01"
    }
    response = client.post(
        "/api/expenses/", json=expense_data, headers=auth_headers)
    return response.json()
