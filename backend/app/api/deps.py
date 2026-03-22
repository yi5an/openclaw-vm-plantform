"""
API dependencies for dependency injection.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database.base import get_db
from app.infrastructure.cache.redis_client import get_redis, RedisClient
from app.infrastructure.database.models import User
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedError, ForbiddenError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        token: JWT token from OAuth2 scheme
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        UnauthorizedError: If token is invalid or user not found
    """
    credentials_exception = UnauthorizedError("Could not validate credentials")
    
    # Decode token
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: Optional[str] = payload.get("sub")
    token_type: Optional[str] = payload.get("type")
    
    if user_id is None or token_type != "access":
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        User: Current active user
        
    Raises:
        ForbiddenError: If user is not active
    """
    if current_user.status != "active":
        raise ForbiddenError("User account is not active")
    
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current admin user.
    
    Args:
        current_user: Current active user
        
    Returns:
        User: Current admin user
        
    Raises:
        ForbiddenError: If user is not an admin
    """
    if current_user.role != "admin":
        raise ForbiddenError("Admin access required")
    
    return current_user


async def get_pagination_params(
    page: int = 1,
    page_size: int = 20
) -> tuple[int, int]:
    """
    Get pagination parameters.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Tuple of (skip, limit)
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100
    
    skip = (page - 1) * page_size
    return skip, page_size
