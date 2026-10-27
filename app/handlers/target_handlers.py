import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx
from fastapi import Form, Request, status
from fastapi.responses import RedirectResponse

from app.services import target_service
from app.utils.redirects import redirect_with_toast
from app.utils.tokens import get_current_user

logger = logging.getLogger(__name__)

AMOUNT_FIELDS = ("short_term_amount", "mid_term_amount", "long_term_amount")
DASHBOARD = "/dashboard"


def parse_amounts(short_term: str, mid_term: str, long_term: str) -> dict:
    """Turn the three form fields into API values.

    A blank field means "no target for this horizon" (None). Amounts are sent as strings so
    the API parses them as exact decimals. Raises ValueError with a message for the user.
    """
    amounts = {}
    for field, raw in zip(AMOUNT_FIELDS, (short_term, mid_term, long_term)):
        text = (raw or "").strip().replace(",", "")
        if not text:
            amounts[field] = None
            continue
        try:
            value = Decimal(text)
        except InvalidOperation:
            raise ValueError("Enter amounts as numbers, for example 1500 or 1500.50")
        if not value.is_finite():
            raise ValueError("Enter amounts as numbers, for example 1500 or 1500.50")
        if value < 0:
            raise ValueError("Amounts cannot be negative")
        if value.as_tuple().exponent < -2:
            raise ValueError("Use at most two decimal places")
        amounts[field] = str(value)
    return amounts


def _error_message(response: httpx.Response, fallback: str) -> str:
    if response.status_code == status.HTTP_404_NOT_FOUND:
        return "That budget, category or target was not found"
    if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        return "Amounts must be numbers that are zero or more"
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = None
    if response.status_code == status.HTTP_400_BAD_REQUEST and isinstance(detail, str):
        return detail
    return fallback


def _failure(response: httpx.Response, fallback: str) -> RedirectResponse:
    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    logger.warning("Target request failed: status=%s", response.status_code)
    return redirect_with_toast(DASHBOARD, _error_message(response, fallback), "error")


async def _call(coro, fallback: str):
    """Run an API call; a network error becomes an error toast instead of a 500 page."""
    try:
        return await coro, None
    except httpx.RequestError:
        return None, redirect_with_toast(DASHBOARD, fallback, "error")


async def save_target(request: Request,
                      budget_id: int = Form(...),
                      category_id: int = Form(...),
                      short_term_amount: Optional[str] = Form(""),
                      mid_term_amount: Optional[str] = Form(""),
                      long_term_amount: Optional[str] = Form("")):
    token = get_current_user(request)
    try:
        amounts = parse_amounts(short_term_amount, mid_term_amount, long_term_amount)
    except ValueError as exc:
        return redirect_with_toast(DASHBOARD, str(exc), "error")

    response, failed = await _call(
        target_service.save_target(token, budget_id, category_id, amounts),
        "Could not reach the server. Try again.")
    if failed:
        return failed
    if response.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED):
        return redirect_with_toast(DASHBOARD, "Target saved", "success")
    return _failure(response, "Target could not be saved")


async def edit_target(request: Request,
                      budget_id: int,
                      target_id: int,
                      short_term_amount: Optional[str] = Form(""),
                      mid_term_amount: Optional[str] = Form(""),
                      long_term_amount: Optional[str] = Form("")):
    token = get_current_user(request)
    try:
        amounts = parse_amounts(short_term_amount, mid_term_amount, long_term_amount)
    except ValueError as exc:
        return redirect_with_toast(DASHBOARD, str(exc), "error")

    response, failed = await _call(
        target_service.update_target(token, budget_id, target_id, amounts),
        "Could not reach the server. Try again.")
    if failed:
        return failed
    if response.status_code == status.HTTP_200_OK:
        return redirect_with_toast(DASHBOARD, "Target updated", "success")
    return _failure(response, "Target could not be updated")


async def delete_target(request: Request, budget_id: int, target_id: int):
    token = get_current_user(request)
    response, failed = await _call(
        target_service.remove_target(token, budget_id, target_id),
        "Could not reach the server. Try again.")
    if failed:
        return failed
    if response.status_code == status.HTTP_204_NO_CONTENT:
        return redirect_with_toast(DASHBOARD, "Target removed", "success")
    return _failure(response, "Target could not be removed")
