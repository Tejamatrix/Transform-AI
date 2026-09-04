from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, what: str = "Resource"):
        super().__init__(f"{what} not found.", 404)


class PermissionError_(AppError):
    def __init__(self):
        super().__init__("You do not have access to this resource.", 403)


class IngestionError(AppError):
    pass


class GenerationError(AppError):
    def __init__(self, msg: str = "Generation failed. You can retry."):
        super().__init__(msg, 502)


async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


async def validation_error_handler(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(p) for p in first.get("loc", []) if p not in ("body",))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": f"Invalid input{' for ' + loc if loc else ''}: {first.get('msg', 'validation failed')}"},
    )


async def unhandled_handler(_: Request, exc: Exception):
    # Never leak stack traces to users.
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again."})
