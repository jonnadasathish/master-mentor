"""Exception → error envelope mapping. Every error response uses ``ErrorEnvelope`` (API_SPEC.md §1)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import AppError
from app.schemas.envelope import ErrorCode, error

logger = logging.getLogger(__name__)


_HTTP_STATUS_CODES: dict[int, ErrorCode] = {
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
    503: ErrorCode.DEPENDENCY_UNAVAILABLE,
}


async def _app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(status_code=exc.status_code, content=error(exc.code, exc.message, exc.details))


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    fields = [
        {
            "loc": [str(part) for part in item.get("loc", ())],
            "msg": item.get("msg", ""),
            "type": item.get("type", ""),
        }
        for item in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error(ErrorCode.VALIDATION_ERROR, "Request validation failed.", {"errors": fields}),
    )


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = _HTTP_STATUS_CODES.get(exc.status_code, ErrorCode.INTERNAL)
    message = exc.detail if isinstance(exc.detail, str) else code.value
    return JSONResponse(status_code=exc.status_code, content=error(code, message), headers=exc.headers)


async def _unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    # Never leak internals (stack traces, SQL, credentials) to the client.
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(status_code=500, content=error(ErrorCode.INTERNAL, "Internal server error."))


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unhandled_error)
