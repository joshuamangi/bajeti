# app/handlers/admin_handlers.py
import logging
from fastapi import Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from app.services.admin_service import fetch_members, reset_access as svc_reset_access
from app.utils.redirects import redirect_with_toast
from app.utils.templates import render_with_user
from app.utils.tokens import get_current_user

logger = logging.getLogger(__name__)
HTMLResponse = HTMLResponse  # expose to router

# The Admin hub is built from this list, so a new section is one entry (PORT-GUIDE §5.10).
# status(members) gives the tag shown on the card.
ADMIN_SECTIONS = [
    {"id": "users", "icon": "fa-users", "title": "Users", "desc": "Household members and access",
     "status": lambda members: f"{len(members)} member{'' if len(members) == 1 else 's'}"},
]


async def _members_or_owner_only(request: Request, token: str):
    """The members list, or the 'Owner only' page (the API answers 404 to everyone else)."""
    response = await fetch_members(token)
    if response.status_code == status.HTTP_200_OK:
        return response.json(), None
    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        return None, RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return None, await render_with_user("admin.html", request, {"active_tab": "more", "owner_only": True})


async def admin_hub(request: Request, token: str = Depends(get_current_user)):
    members, page = await _members_or_owner_only(request, token)
    if page:
        return page
    sections = [{**s, "status_text": s["status"](members)} for s in ADMIN_SECTIONS]
    return await render_with_user("admin.html", request, {"active_tab": "more", "sections": sections})


async def admin_users(request: Request, token: str = Depends(get_current_user)):
    return await _render_users(request, token)


async def _render_users(request: Request, token: str, reset_link=None):
    members, page = await _members_or_owner_only(request, token)
    if page:
        return page
    return await render_with_user("admin_users.html", request, {
        "active_tab": "more", "members": members, "reset_link": reset_link})


async def reset_access(request: Request, user_id: int, token: str = Depends(get_current_user)):
    response = await svc_reset_access(token, user_id)
    if response.status_code != status.HTTP_201_CREATED:
        if response.status_code == status.HTTP_404_NOT_FOUND:
            return redirect_with_toast("/admin/users", "User not found", "error")
        try:
            detail = response.json().get("detail", "Could not reset access")
        except Exception:
            detail = "Could not reset access"
        return redirect_with_toast("/admin/users", str(detail), "error")

    # Rendered, not redirected: the link must not end up in a URL or in the browser history.
    link = response.json()
    member = next((m for m in (await fetch_members(token)).json() if m["id"] == user_id), {})
    return await _render_users(request, token, reset_link={
        "path": f"/reset#{link['token']}",
        "expires_at": link["expires_at"],
        "name": f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
    })
