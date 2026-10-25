"""Registration switch."""
from fastapi import HTTPException, status

from app.config import settings


def require_registration_open() -> None:
    """Dependency: 404 (as if the page did not exist) while registration is closed."""
    if not settings.REGISTRATION_OPEN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
