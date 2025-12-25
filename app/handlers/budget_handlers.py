from datetime import datetime
from fastapi import Depends, Form, Request, status
from fastapi.responses import RedirectResponse

from app.services.budget_service import edit_budget, get_budget
from app.utils.redirects import redirect_with_toast
from app.utils.templates import render_with_user
from app.utils.tokens import get_current_user
from app.services.auth_service import get_current_user as svc_get_current_user


async def update_budget(request: Request,
                        budget_id: int,
                        budget_amount: float = Form(...),
                        budget_name: str = Form(...),
                        token: str = Depends(get_current_user)):
    token = get_current_user(request)
    resp = await edit_budget(token=token, budget_name=budget_name, amount=budget_amount, budget_id=budget_id)

    if resp.status_code == status.HTTP_200_OK:
        return redirect_with_toast(
            base_url="/dashboard",
            message="Amount updated successfully",
            type_="success",)

    user_response = await svc_get_current_user(token)
    if user_response.status_code != status.HTTP_200_OK:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    user = user_response.json()
    return await render_with_user("dashboard.html", request, {
        "error": "Budget edit failed",
        "token": token,
        "categories_with_stats": [],
        "budget_allocations": [],
        "budget_details": {},
        "current_month": datetime.now().strftime('%B'),
        "user": user,
        "now": datetime.now().strftime("%Y-%m"),
    })
