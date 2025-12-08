# app/handlers/page_handlers.py
from fastapi import Request
from fastapi.responses import HTMLResponse
from app.utils.templates import render_with_user

HTMLResponse = HTMLResponse


async def reports_page(request: Request):
    return await render_with_user("reports.html", request)


async def analytics_page(request: Request):
    return await render_with_user("analytics.html", request)


async def settings_page(request: Request):
    return await render_with_user("settings.html", request)
