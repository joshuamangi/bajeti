from typing import Any
from fastapi import status
from fastapi.responses import JSONResponse
from core.messages import get_message, MessageCode, MessageType


class ApiResponse:
    """Standardized API response"""

    @staticmethod
    def success(
        message_code: MessageCode,
        data: Any = None,
        status_code: int = status.HTTP_200_OK,
        **message_kwargs
    ):

        message = get_message(message_code, **message_kwargs)
        return JSONResponse(
            status_code=status_code,
            content={
                "success": True,
                "message": message["text"],
                "message_code": message["code"],
                "message_type": message["type"],
                "data": data or {}
            }
        )

    @staticmethod
    def error(
        message_code: MessageCode,
        errors: list = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        **message_kwargs
    ):
        message = get_message(message_code, **message_kwargs)
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "message": message["text"],
                "message_code": message["code"],
                "message_type": message["type"],
                "errors": errors or [],
                "data": {}
            }
        )
