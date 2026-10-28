# app/utils/templates.py
import os
from decimal import Decimal, InvalidOperation
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict
from fastapi import Request
from app.config import ENVIRONMENT, settings
import logging

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["ENVIRONMENT"] = ENVIRONMENT
# A function, so the page follows the setting at request time.
templates.env.globals["registration_open"] = lambda: settings.REGISTRATION_OPEN


def commafy(value, decimals=0):
    try:
        num_value = float(value)
        if decimals == 0:
            return f"{int(num_value):,}"
        else:
            return f"{num_value:,.{decimals}f}"
    except (ValueError, TypeError):
        return value


def money_text(value, decimals=None, sign=False):
    """Thousands separators and 0 or 2 decimals (0 when the amount is whole), as in Prototype A.
    Negative amounts use a real minus sign; sign=True adds "+" to positive ones."""
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return value
    if decimals is None:
        decimals = 0 if amount == amount.to_integral_value() else 2
    body = f"{abs(amount):,.{decimals}f}"
    if amount < 0 and body.strip("0.,"):
        return "−" + body
    if sign and amount > 0:
        return "+" + body
    return body


STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


def asset(path: str) -> str:
    """URL of a static file with its modification time as ?v=, so a changed file is never
    served from an old browser cache."""
    try:
        version = int(os.stat(os.path.join(STATIC_DIR, path)).st_mtime)
    except OSError:
        return f"/static/{path}"
    return f"/static/{path}?v={version}"


templates.env.globals["asset"] = asset

# register filter
templates.env.filters["commafy"] = commafy
templates.env.filters["money_text"] = money_text


async def render_with_user(template_name: str, request: Request, context: Optional[Dict] = None):
    """Render templates with global user context. Handlers call get_user_from_cookie before this."""
    if context is None:
        context = {}
    context.update({"request": request})
    return templates.TemplateResponse(template_name, context)
