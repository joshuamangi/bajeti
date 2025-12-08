# app/utils/redirects.py
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
from fastapi import status


def redirect_with_toast(base_url: str, message: str, type_: str = "success", status_code: int = status.HTTP_303_SEE_OTHER):
    params = urlencode({"toast": type_, "message": message})
    return RedirectResponse(url=f"{base_url}?{params}", status_code=status_code)
