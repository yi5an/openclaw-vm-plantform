"""
Authentication API endpoints: register, login, token refresh.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from app.infrastructure.database.base import get_db
from app.infrastructure.database.models import User, UserRole, UserStatus
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError, BadRequestError
from app.core.response import success_response

router = APIRouter()


# Request/Response Models
class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    username: str = Field(..., min_length=3, max_length=100)


class UserResponse(BaseModel):
    """User response model."""
    id: str
    email: str
    username: str
    balance: float
    role: str
    created_at: str
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user.
    
    Args:
        request: Registration request with email, password, and username
        db: Database session
        
    Returns:
        Created user information
        
    Raises:
        ConflictError: If email or username already exists
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise ConflictError("Email already registered")
    
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise ConflictError("Username already taken")
    
    # Create new user
    user = User(
        email=request.email,
        username=request.username,
        password_hash=hash_password(request.password),
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        balance=0.00
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    user_data = UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        balance=float(user.balance),
        role=user.role.value,
        created_at=user.created_at.isoformat()
    )
    
    return success_response(user_data.dict(), "User registered successfully")


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login and get access token.
    
    Args:
        form_data: OAuth2 form with username (email) and password
        db: Database session
        
    Returns:
        Access and refresh tokens
        
    Raises:
        UnauthorizedError: If credentials are invalid
    """
    # Find user by email (username field contains email)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.password_hash):
        raise UnauthorizedError("Incorrect email or password")
    
    # Check if user is active
    if user.status != UserStatus.ACTIVE:
        raise UnauthorizedError("User account is not active")
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    
    token_data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return success_response(token_data.dict(), "Login successful")


@router.post("/refresh")
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    Args:
        request: Refresh token request
        db: Database session
        
    Returns:
        New access and refresh tokens
        
    Raises:
        UnauthorizedError: If refresh token is invalid
    """
    # Decode refresh token
    payload = decode_token(request.refresh_token)
    if payload is None:
        raise UnauthorizedError("Invalid refresh token")
    
    user_id = payload.get("sub")
    token_type = payload.get("type")
    
    if not user_id or token_type != "refresh":
        raise UnauthorizedError("Invalid refresh token")
    
    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or user.status != UserStatus.ACTIVE:
        raise UnauthorizedError("User not found or inactive")
    
    # Create new tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    
    token_data = TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return success_response(token_data.dict(), "Token refreshed successfully")
