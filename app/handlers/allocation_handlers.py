from datetime import datetime
import logging
from fastapi import Depends, Form, Request, status
from fastapi.responses import RedirectResponse

from app.services import allocation_service
from app.utils.redirects import redirect_with_toast
from app.utils.templates import render_with_user
from app.utils.tokens import get_current_user
from app.services.auth_service import get_current_user as svc_get_current_user

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def add_allocation(request: Request,
                         allocated_amount: float = Form(...),
                         category_id: int = Form(...),
                         budget_id: int = Form(...),
                         token: str = Depends(get_current_user)):
    logger.info("Allocation request: category_id=%s, budget_id=%s, amount=%s",
                category_id, budget_id, allocated_amount)
    token = get_current_user(request)
    allocation_response = await allocation_service.create_allocation(
        token=token,
        allocated_amount=allocated_amount,
        budget_id=budget_id,
        category_id=category_id)

    if allocation_response.status_code == status.HTTP_201_CREATED:
        return redirect_with_toast("/dashboard", "Allocation created successfully!", "success")
    if allocation_response.status_code == status.HTTP_409_CONFLICT:
        return redirect_with_toast("/dashboard", "Allocation already exists!", "error")
    user_response = await svc_get_current_user(token)

    if user_response.status_code != status.HTTP_200_OK:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    user = user_response.json()
    return await render_with_user("dashboard.html", request, {
        "error": "Allocation creation failed",
        "token": token,
        "categories_with_stats": [],
        "budget_allocations": [],
        "budget_details": {},
        "current_month": datetime.now().strftime('%B'),
        "user": user,
        "now": datetime.now().strftime("%Y-%m"),
    })


async def edit_allocation(request: Request,
                          budget_id: int,
                          allocated_amount: float = Form(...),
                          category_id: int = Form(...)):
    token = get_current_user(request)
    allocation_response = await allocation_service.update_allocation(
        allocated_amount=allocated_amount,
        budget_id=budget_id,
        category_id=category_id,
        token=token
    )
    if allocation_response.status_code == status.HTTP_200_OK:
        return redirect_with_toast(base_url="/dashboard",
                                   message="Allocation updated successfully",
                                   type_="success",)

    user_response = await svc_get_current_user(token)

    if user_response.status_code != status.HTTP_200_OK:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    user = user_response.json()
    return await render_with_user("dashboard.html", request, {
        "error": "Allocation update failed",
        "token": token,
        "categories_with_stats": [],
        "budget_allocations": [],
        "budget_details": {},
        "current_month": datetime.now().strftime('%B'),
        "user": user,
        "now": datetime.now().strftime("%Y-%m"),
    })


async def delete_allocation(request: Request,
                            budget_id: int,
                            allocation_id: int):
    token = get_current_user(request)
    allocation_response = await allocation_service.remove_allocation(token=token,
                                                                     budget_id=budget_id,
                                                                     allocation_id=allocation_id)

    if allocation_response.status_code == status.HTTP_204_NO_CONTENT:
        return redirect_with_toast(base_url="/dashboard",
                                   message="Allocation removed successfully",
                                   type_="success",)
    user_response = await svc_get_current_user(token)

    if user_response.status_code != status.HTTP_200_OK:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    user = user_response.json()
    return await render_with_user("dashboard.html", request, {
        "error": "Allocation deletion failed",
        "token": token,
        "categories_with_stats": [],
        "budget_allocations": [],
        "budget_details": {},
        "current_month": datetime.now().strftime('%B'),
        "user": user,
        "now": datetime.now().strftime("%Y-%m"),
    })
