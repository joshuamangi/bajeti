from fastapi import Depends, Form, Request, status

from app.services.budget_service import add_budget, delete_budget, edit_budget, get_active_budget
from app.utils.redirects import redirect_with_toast
from app.utils.tokens import get_current_user


async def create_budget(request: Request,
                        budget_amount: float = Form(...),
                        budget_name: str = Form(...),
                        budget_type: str = Form(...),
                        token: str = Depends(get_current_user)):
    token = get_current_user(request)
    resp = await add_budget(token=token,
                            amount=budget_amount,
                            budget_name=budget_name,
                            budget_type=budget_type)

    if resp.status_code == status.HTTP_201_CREATED:
        return redirect_with_toast(
            base_url="/dashboard",
            message="Budget created successfully",
            type_="success",
        )

    if resp.status_code == status.HTTP_409_CONFLICT:
        return redirect_with_toast(
            base_url="/dashboard",
            message="Budget already exists",
            type_="error",
        )

    return redirect_with_toast("/dashboard", "Budget creation failed", "error")


async def update_budget(request: Request,
                        budget_id: int,
                        budget_amount: float = Form(...),
                        budget_type: str = Form(...),
                        budget_name: str = Form(...),
                        token: str = Depends(get_current_user)):
    token = get_current_user(request)
    resp = await edit_budget(token=token, budget_name=budget_name, amount=budget_amount, budget_id=budget_id, budget_type=budget_type)

    if resp.status_code == status.HTTP_200_OK:
        return redirect_with_toast(
            base_url="/dashboard",
            message="Budget updated successfully",
            type_="success",)

    return redirect_with_toast("/dashboard", "Budget edit failed", "error")


async def remove_budget(request: Request,
                        budget_id: int):
    token = get_current_user(request)
    budget_response = await delete_budget(token=token, budget_id=budget_id)

    if budget_response.status_code == status.HTTP_204_NO_CONTENT:
        return redirect_with_toast(
            base_url="/dashboard",
            message="Budget deleted successfully",
            type_="success",)

    return redirect_with_toast("/dashboard", "Budget deletion failed", "error")
