"""Exception handlers for converting exceptions to JSEND format."""

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.jsend import error_response, fail_response
from src.logging_config import get_logger

logger = get_logger(__name__)


def _handle_4xx_error(exc: HTTPException) -> dict:
    """Handle 4xx client errors and convert to JSEND fail format."""
    status_code = exc.status_code
    detail = exc.detail

    if status_code == status.HTTP_400_BAD_REQUEST:
        # Bad request - validation or input errors
        if isinstance(detail, dict):
            data = detail
        elif isinstance(detail, list):
            data = {"validation_errors": detail}
        else:
            data = {"message": detail}
        return fail_response(data)
    elif status_code == status.HTTP_401_UNAUTHORIZED:
        return fail_response({"message": detail or "Authentication required"})
    elif status_code == status.HTTP_403_FORBIDDEN:
        return fail_response({"message": detail or "Access forbidden"})
    elif status_code == status.HTTP_404_NOT_FOUND:
        return fail_response({"message": detail or "Resource not found"})
    elif status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return fail_response({"message": detail or "Rate limit exceeded"})
    elif status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
        return fail_response({"message": detail or "Request too large"})
    else:
        # Other 4xx errors
        if isinstance(detail, dict):
            data = detail
        else:
            data = {"message": detail}
        return fail_response(data)


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Convert HTTPExceptions to JSEND format.
    - 4xx errors (except 400) -> fail status
    - 5xx errors -> error status
    - 400 errors -> fail status (validation errors)
    """
    status_code = exc.status_code

    # Determine JSEND status based on HTTP status code
    if 400 <= status_code < 500:
        # Client errors: use "fail" status
        response_data = _handle_4xx_error(exc)
    else:
        # Server errors (5xx): use "error" status
        response_data = error_response(message=exc.detail or "Internal server error", code=status_code)

    return JSONResponse(status_code=status_code, content=response_data)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Convert FastAPI validation errors to JSEND fail format.
    """
    errors = {}
    for error in exc.errors():
        # Extract field path and message
        field_path = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        if not field_path:
            field_path = "request"

        if field_path not in errors:
            errors[field_path] = []
        errors[field_path].append(error["msg"])

    # Convert to single string messages per field
    error_data = {field: messages[0] if len(messages) == 1 else messages for field, messages in errors.items()}

    response_data = fail_response(error_data)
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=response_data)


async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions and convert to JSEND error format.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    response_data = error_response(
        message="An unexpected error occurred",
        code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response_data)
