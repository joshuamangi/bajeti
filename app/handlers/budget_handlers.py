from datetime import datetime
from fastapi import Depends, Form, Request, status

from app.services.budget_service import edit_budget, get_budget
from app.utils.redirects import redirect_with_toast
from app.utils.templates import render_with_user
from app.utils.tokens import get_current_user


async def update_budget(request: Request,
                        budget_id: int,
                        amount: float = Form(...),
                        token: str = Depends(get_current_user)):
    token = get_current_user(request)
    resp = await edit_budget(token=token, amount=amount, budget_id=budget_id)

    if resp.status_code == status.HTTP_200_OK:
        return redirect_with_toast(
            base_url="dashboard.html",
            message="Amount changed successfully",
            type_="success",)
    return render_with_user(
        template_name="/dashboard",
        request=request,
        context={
            "error": "Budget update failed",
            "token": token,
            "budget_details": [],
            "now": datetime.now().strftime("%Y-%m"),
        }
    )
