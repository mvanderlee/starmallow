from starlette.exceptions import HTTPException
from starlette.requests import Request

from starmallow.exceptions import RequestValidationError
from starmallow.responses import JSONResponse


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    headers = getattr(exc, "headers", None)
    if headers:
        return JSONResponse(
            {"detail": exc.detail}, status_code=exc.status_code, headers=headers,
        )
    else:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.errors,
            "error": "ValidationError",
            "status_code": exc.status_code,
        },
    )
