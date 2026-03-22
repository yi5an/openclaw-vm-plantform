"""
Custom exception classes and exception handlers for the application.
"""
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional


class AppException(Exception):
    """Base exception class for application errors."""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code or "APP_ERROR"
        self.headers = headers
        super().__init__(self.detail)


class NotFoundError(AppException):
    """Resource not found exception."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with id '{identifier}' not found",
            error_code="NOT_FOUND"
        )


class UnauthorizedError(AppException):
    """Unauthorized access exception."""
    
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenError(AppException):
    """Forbidden access exception."""
    
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN"
        )


class BadRequestError(AppException):
    """Bad request exception."""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="BAD_REQUEST"
        )


class ConflictError(AppException):
    """Conflict exception (e.g., duplicate resource)."""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT"
        )


class InsufficientBalanceError(AppException):
    """Insufficient balance exception."""
    
    def __init__(self, required: float, available: float):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient balance. Required: {required}, Available: {available}",
            error_code="INSUFFICIENT_BALANCE"
        )


class VMOperationError(AppException):
    """VM operation failed exception."""
    
    def __init__(self, operation: str, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"VM {operation} failed: {detail}",
            error_code="VM_OPERATION_ERROR"
        )


class RateLimitExceededError(AppException):
    """Rate limit exceeded exception."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            error_code="RATE_LIMIT_EXCEEDED",
            headers={"Retry-After": str(retry_after)}
        )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global exception handler for AppException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                "status_code": exc.status_code
            }
        },
        headers=exc.headers
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unexpected errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "status_code": 500
            }
        }
    )


def setup_exception_handlers(app):
    """Setup exception handlers for the FastAPI application."""
    app.add_exception_handler(AppException, app_exception_handler)
    # Uncomment in production to catch all unexpected errors
    # app.add_exception_handler(Exception, generic_exception_handler)
