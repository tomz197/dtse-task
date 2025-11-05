import time

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.logging_config import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "client": request.client.host if request.client else None,
                }
            },
        )

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(
                f"Response: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "process_time": process_time,
                    }
                },
            )
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} - Error: {str(e)} - Time: {process_time:.3f}s",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "process_time": process_time,
                    }
                },
            )
            raise


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit the size of incoming requests."""
    
    def __init__(self, app, max_request_size_mb: int = 10):
        super().__init__(app)
        self.max_request_size = max_request_size_mb * 1024 * 1024
    
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("content-length"):
            content_length = int(request.headers.get("content-length", 0))
            if content_length > self.max_request_size:
                logger.warning(
                    f"Request size {content_length} exceeds limit {self.max_request_size} "
                    f"for {request.method} {request.url.path}"
                )
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Request too large. Maximum size: {self.max_request_size / 1024 / 1024}MB"
                )
        response = await call_next(request)
        return response

