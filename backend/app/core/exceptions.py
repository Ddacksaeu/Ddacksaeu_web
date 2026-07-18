from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers={"X-Request-ID": request.state.request_id},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    messages = {
        404: "Resource not found",
        405: "Method not allowed",
    }
    return error_response(
        request,
        exc.status_code,
        f"http_{exc.status_code}",
        messages.get(exc.status_code, "Request failed"),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return error_response(request, 422, "validation_error", "Request validation failed")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("ddacksaeu").exception(
        "Unhandled application error", extra={"request_id": request.state.request_id}
    )
    return error_response(request, 500, "internal_error", "Internal server error")
