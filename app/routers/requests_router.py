# app/routers/requests_router.py
from fastapi import APIRouter

from app.handlers import (
    auth_handlers,
    dashboard_handlers,
    category_handlers,
    expense_handlers,
    page_handlers,
    transfer_handlers
)

router = APIRouter()

# ---------- AUTH ----------
router.get("/", response_class=auth_handlers.HTMLResponse)(auth_handlers.welcome)
router.get("/register",
           response_class=auth_handlers.HTMLResponse)(auth_handlers.register_page)
router.post("/register")(auth_handlers.register_user)
router.get(
    "/login", response_class=auth_handlers.HTMLResponse)(auth_handlers.login_page)
router.post("/login")(auth_handlers.login_user)
router.get("/logout")(auth_handlers.logout)
router.get("/forgot_password",
           response_class=auth_handlers.HTMLResponse)(auth_handlers.forgot_password)
router.post("/forgot_password")(auth_handlers.reset_password)

# ---------- PROFILE & DASHBOARD ----------
router.get(
    "/profile", response_class=dashboard_handlers.HTMLResponse)(dashboard_handlers.profile)
router.post("/profile/update")(dashboard_handlers.profile_update)
router.get("/dashboard",
           response_class=dashboard_handlers.HTMLResponse)(dashboard_handlers.dashboard)

# ---------- CATEGORY CRUD ----------
router.post("/dashboard/categories")(category_handlers.add_category)
router.post(
    "/dashboard/categories/{category_id}/edit")(category_handlers.edit_category)
router.post(
    "/dashboard/categories/{category_id}/delete")(category_handlers.delete_category)

# ---------- EXPENSE CRUD ----------
router.post("/dashboard/expenses")(expense_handlers.add_expense)
router.post(
    "/dashboard/expenses/{expense_id}/edit")(expense_handlers.edit_expense)
router.post(
    "/dashboard/expenses/{expense_id}/delete")(expense_handlers.delete_expense)

# ---------- TRANSFER CRUD ----------
router.post("/dashboard/transfers")(transfer_handlers.add_transfer)
router.post(
    "/dashboard/transfers/{transfer_id}/undo")(transfer_handlers.undo_transfer)

# ---------- STATIC PAGES ----------
router.get(
    "/reports", response_class=page_handlers.HTMLResponse)(page_handlers.reports_page)
router.get("/analytics",
           response_class=page_handlers.HTMLResponse)(page_handlers.analytics_page)
router.get("/settings",
           response_class=page_handlers.HTMLResponse)(page_handlers.settings_page)
