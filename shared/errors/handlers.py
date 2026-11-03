from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.errors.exceptions import AppException


async def app_exception_handler(
    request: Request,
    exc: AppException
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "retry_after": exc.retry_after
            }
        }
    )


def register_error_handlers(app: FastAPI):
    app.add_exception_handler(
        AppException,
        app_exception_handler
    )