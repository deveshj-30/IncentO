"""Common error shape (code, message, request_id) for every error response."""

import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import ApiError
from app.core.schemas import ErrorCode, ErrorResponse

log = logging.getLogger("incento")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:12]}"
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        return response


def error_response(
    request: Request, status: int, code: ErrorCode, message: str, details: list[str] | None = None
):
    body = ErrorResponse(
        code=code,
        message=message,
        request_id=getattr(request.state, "request_id", "req-unknown"),
        details=details or [],
    )
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


def install_error_handlers(app: FastAPI) -> None:
    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(ApiError)
    async def _api(request: Request, exc: ApiError):
        return error_response(request, exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        details = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
        return error_response(request, 422, ErrorCode.VALIDATION_ERROR, "Request validation failed", details)

    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException):
        codes = {404: ErrorCode.NOT_FOUND, 501: ErrorCode.NOT_IMPLEMENTED}
        code = codes.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        return error_response(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        log.exception("unhandled error (request_id=%s)", getattr(request.state, "request_id", "unknown"))
        return error_response(request, 500, ErrorCode.INTERNAL_ERROR, "Unexpected server error")
