# app/handlers/payment_handlers.py
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import Depends, Form, Request, status
from fastapi.responses import HTMLResponse

from app.handlers.dashboard_handlers import render_app_page
from app.services import payment_service
from app.utils.redirects import redirect_with_toast
from app.utils.templates import money_text
from app.utils.tokens import get_current_user

HTMLResponse = HTMLResponse  # expose to router
PAGE = "/payments"


def _detail(resp, fallback: str) -> str:
    try:
        detail = resp.json().get("detail", fallback)
    except ValueError:
        return fallback
    return detail if isinstance(detail, str) else fallback


async def payments_page(request: Request, token: str = Depends(get_current_user), budget_id: Optional[int] = None):
    async def extra(context, active_id):
        if not active_id:
            return {"inbox": None}
        response = await payment_service.fetch_pending(token, active_id)
        return {"inbox": response.json() if response.status_code == status.HTTP_200_OK else None}
    return await render_app_page("payments.html", "more", request, token, budget_id, extra_async=extra)


async def capture_payment(request: Request, raw: str = Form(...)):
    token = get_current_user(request)
    if len(raw) > 2000:
        return redirect_with_toast(PAGE, "Paste one message at a time (up to 2,000 characters).", "error")
    resp = await payment_service.capture(token, raw)
    if resp.status_code == status.HTTP_201_CREATED:
        p = resp.json()["payment"]
        if p["amount"] is None:
            return redirect_with_toast(PAGE, "Couldn't read this message. It is in the inbox to fill in.", "warning")
        return redirect_with_toast(PAGE, f"Added {p['payee'] or 'payment'}, KES {money_text(p['total'])}", "success")
    if resp.status_code == status.HTTP_200_OK:
        return redirect_with_toast(PAGE, resp.json().get("reason", "Not added."), "info")
    if resp.status_code == status.HTTP_409_CONFLICT:
        return redirect_with_toast(PAGE, _detail(resp, "Already captured"), "warning")
    return redirect_with_toast(PAGE, "Couldn't read that. Paste one message at a time.", "error")


async def approve_payment(request: Request, payment_id: int, category_id: int = Form(...),
                          amount: str = Form(""), remember: str = Form("")):
    token = get_current_user(request)
    payload = {"category_id": category_id, "remember": remember in ("1", "on", "true")}
    if amount.strip():
        try:
            value = Decimal(amount.replace(",", "").strip())
        except InvalidOperation:
            return redirect_with_toast(PAGE, "Enter the amount as a number.", "error")
        payload["amount"] = format(value.quantize(Decimal("0.01")), "f")
    resp = await payment_service.approve(token, payment_id, payload)
    if resp.status_code == status.HTTP_201_CREATED:
        data = resp.json()
        return redirect_with_toast(PAGE, f"Added KES {money_text(data['amount'])}", "success")
    return redirect_with_toast(PAGE, _detail(resp, "Could not add this payment."), "error")


async def dismiss_payment(request: Request, payment_id: int):
    token = get_current_user(request)
    resp = await payment_service.dismiss(token, payment_id)
    if resp.status_code == status.HTTP_204_NO_CONTENT:
        return redirect_with_toast(PAGE, "Dismissed", "warning")
    return redirect_with_toast(PAGE, _detail(resp, "Could not dismiss it."), "error")


async def restore_payment(request: Request, payment_id: int):
    token = get_current_user(request)
    resp = await payment_service.restore(token, payment_id)
    if resp.status_code == status.HTTP_204_NO_CONTENT:
        return redirect_with_toast(PAGE, "Back in the inbox", "info")
    return redirect_with_toast(PAGE, _detail(resp, "Could not undo it."), "error")
