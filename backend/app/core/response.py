"""
Unified API response wrapper for consistent response format across all endpoints.

All API responses should use this wrapper to ensure the frontend receives
a consistent structure: { success: true/false, data: {...}, message: "..." }
"""
from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """
    Unified API response model.
    
    Attributes:
        success: Whether the request was successful
        data: Response data (can be any type)
        message: Optional success message
        error: Optional error message (only present when success=False)
    """
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None
    
    class Config:
        # Allow arbitrary types for data field
        arbitrary_types_allowed = True


def success_response(data: Any = None, message: Optional[str] = None) -> dict:
    """
    Create a success response wrapper.
    
    Args:
        data: Response data (can be dict, list, Pydantic model, etc.)
        message: Optional success message
        
    Returns:
        Dict with success=True and wrapped data
        
    Example:
        >>> return success_response({"user": user_data}, "User created successfully")
        {"success": true, "data": {"user": {...}}, "message": "User created successfully"}
    """
    # Convert Pydantic models to dict if needed
    if hasattr(data, 'dict'):
        data = data.dict()
    elif hasattr(data, 'model_dump'):
        data = data.model_dump()
    
    response = APIResponse(
        success=True,
        data=data,
        message=message
    )
    return response.dict(exclude_none=True)


def error_response(
    message: str, 
    error: Optional[str] = None, 
    error_code: Optional[str] = None
) -> dict:
    """
    Create an error response wrapper.
    
    Args:
        message: Error message for users
        error: Optional technical error details
        error_code: Optional error code for frontend handling
        
    Returns:
        Dict with success=False and error details
        
    Example:
        >>> return error_response("User not found", "USER_NOT_FOUND")
        {"success": false, "message": "User not found", "error": "USER_NOT_FOUND"}
    """
    response = APIResponse(
        success=False,
        message=message,
        error=error or error_code
    )
    return response.dict(exclude_none=True)


def paginated_response(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: Optional[str] = None
) -> dict:
    """
    Create a paginated response wrapper.
    
    Args:
        items: List of items for current page
        total: Total number of items
        page: Current page number
        page_size: Items per page
        message: Optional success message
        
    Returns:
        Dict with success=True and paginated data
        
    Example:
        >>> return paginated_response(users, total=100, page=1, page_size=10)
        {
            "success": true,
            "data": {
                "items": [...],
                "total": 100,
                "page": 1,
                "page_size": 10,
                "pages": 10
            }
        }
    """
    pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    data = {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages
    }
    
    return success_response(data, message)
