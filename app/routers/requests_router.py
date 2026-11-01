# app/routers/requests_router.py
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.handlers import (
    admin_handlers,
    allocation_handlers,
    auth_handlers,
    budget_handlers,
    dashboard_handlers,
    category_handlers,
    expense_handlers,
    page_handlers,
    analytics_handlers,
    recurring_handlers,
    payment_handlers,
    target_handlers,
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
router.post("/logout-all")(auth_handlers.logout_all)
router.get("/forgot_password",
           response_class=auth_handlers.HTMLResponse)(auth_handlers.forgot_password)
router.post("/forgot_password")(auth_handlers.reset_password)
router.get("/reset", response_class=auth_handlers.HTMLResponse)(auth_handlers.reset_link_page)
router.post("/reset")(auth_handlers.reset_link_submit)

# ---------- PROFILE & DASHBOARD ----------
router.get(
    "/profile", response_class=dashboard_handlers.HTMLResponse)(dashboard_handlers.profile)
router.post("/profile/update")(dashboard_handlers.profile_update)
router.post("/profile/security-question")(dashboard_handlers.security_question_update)
router.get("/profile/password",
           response_class=dashboard_handlers.HTMLResponse)(dashboard_handlers.change_password_page)
router.post("/profile/password")(dashboard_handlers.change_password)
router.post("/profile/phone-tokens",
            response_class=dashboard_handlers.HTMLResponse)(dashboard_handlers.create_phone_token)
# Back or refresh after creating a token: return to the Account page (the token is not shown again).
router.get("/profile/phone-tokens")(lambda: RedirectResponse(url="/profile", status_code=303))
router.post("/profile/phone-tokens/{token_id}/revoke")(dashboard_handlers.revoke_phone_token)
router.get("/dashboard",
           response_class=dashboard_handlers.HTMLResponse)(dashboard_handlers.dashboard)
router.get("/budgets",
           response_class=dashboard_handlers.HTMLResponse)(dashboard_handlers.budgets_page)
router.get("/recurring",
           response_class=recurring_handlers.HTMLResponse)(recurring_handlers.recurring_page)
router.post("/recurring")(recurring_handlers.add_recurring)
router.post("/recurring/{recurring_id}/edit")(recurring_handlers.edit_recurring)
router.post("/recurring/{recurring_id}/delete")(recurring_handlers.delete_recurring)
router.post("/recurring/{recurring_id}/runs/{due_date}/undo")(recurring_handlers.undo_recurring_run)
router.post("/recurring/{recurring_id}/{name}")(recurring_handlers.recurring_action)
router.get("/payments",
           response_class=payment_handlers.HTMLResponse)(payment_handlers.payments_page)
router.post("/payments/capture")(payment_handlers.capture_payment)
router.post("/payments/{payment_id}/approve")(payment_handlers.approve_payment)
router.post("/payments/{payment_id}/recurring")(payment_handlers.file_payment_recurring)
router.post("/payments/{payment_id}/savings")(payment_handlers.file_payment_savings)
router.post("/payments/{payment_id}/dismiss")(payment_handlers.dismiss_payment)
router.post("/payments/{payment_id}/restore")(payment_handlers.restore_payment)
router.get("/more",
           response_class=dashboard_handlers.HTMLResponse)(dashboard_handlers.more_page)

# ---------- ADMIN (owner only) ----------
router.get("/admin", response_class=admin_handlers.HTMLResponse)(admin_handlers.admin_hub)
router.get("/admin/users", response_class=admin_handlers.HTMLResponse)(admin_handlers.admin_users)
router.post("/admin/users/{user_id}/reset-access")(admin_handlers.reset_access)

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

# ---------- BUDGET CRUD ----------
router.post(
    "/dashboard/budgets/{budget_id}/edit")(budget_handlers.update_budget)
router.post("/dashboard/budgets")(budget_handlers.create_budget)
router.post("/dashboard/budgets/{budget_id}/default")(budget_handlers.default_budget)
router.post("/dashboard/{budget_id}/delete")(budget_handlers.remove_budget)
# ---------- ALLOCATIONS CRUD ------------
router.post("/dashboard/allocations")(allocation_handlers.add_allocation)
router.post(
    "/dashboard/allocations/{budget_id}/edit")(allocation_handlers.edit_allocation)
router.post(
    "/dashboard/allocations/{budget_id}/delete/{allocation_id}")(allocation_handlers.delete_allocation)
# ---------- TARGETS ------------
router.post("/dashboard/targets")(target_handlers.save_target)
router.post(
    "/dashboard/targets/{budget_id}/{target_id}/edit")(target_handlers.edit_target)
router.post(
    "/dashboard/targets/{budget_id}/{target_id}/delete")(target_handlers.delete_target)
# ---------- STATIC PAGES ----------
router.get(
    "/reports", response_class=page_handlers.HTMLResponse)(page_handlers.reports_page)
router.get("/analytics")(analytics_handlers.analytics_home)
# Fixed paths before /analytics/{month}
router.get("/analytics/trends",
           response_class=analytics_handlers.HTMLResponse)(analytics_handlers.analytics_trends)
router.get("/analytics/year",
           response_class=analytics_handlers.HTMLResponse)(analytics_handlers.analytics_year)
router.get("/analytics/year/{year}",
           response_class=analytics_handlers.HTMLResponse)(analytics_handlers.analytics_year)
router.get("/analytics/{month}",
           response_class=analytics_handlers.HTMLResponse)(analytics_handlers.analytics_month)
router.get("/analytics/{month}/{category_id}",
           response_class=analytics_handlers.HTMLResponse)(analytics_handlers.analytics_category)
router.get("/settings",
           response_class=page_handlers.HTMLResponse)(page_handlers.settings_page)
