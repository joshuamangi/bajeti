# app/utils/templates.py
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict
from fastapi import Request
from app.config import ENVIRONMENT
import logging

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["ENVIRONMENT"] = ENVIRONMENT


def commafy(value, decimals=0):
    try:
        num_value = float(value)
        if decimals == 0:
            return f"{int(num_value):,}"
        else:
            return f"{num_value:,.{decimals}f}"
    except (ValueError, TypeError):
        return value


# register filter
templates.env.filters["commafy"] = commafy


async def render_with_user(template_name: str, request: Request, context: Optional[Dict] = None):
    """Render templates with global user context. Handlers call get_user_from_cookie before this."""
    if context is None:
        context = {}
    context.update({"request": request})
    return templates.TemplateResponse(template_name, context)
