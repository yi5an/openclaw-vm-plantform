"""
User management API endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from app.infrastructure.database.base import get_db
from app.infrastructure.database.models import User, Order
from app.api.deps import get_current_active_user
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.response import success_response

router = APIRouter()


# Request/Response Models
class UserResponse(BaseModel):
    """User response model."""
    id: str
    email: str
    username: str
    balance: float
    role: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """User update request."""
    username: str = Field(None, min_length=3, max_length=100)


class RechargeRequest(BaseModel):
    """Recharge balance request."""
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., pattern="^(alipay|wechat|bank)$")


class RechargeResponse(BaseModel):
    """Recharge response."""
    order_id: str
    amount: float
    payment_url: str
    status: str


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information
    """
    user_data = UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        balance=float(current_user.balance),
        role=current_user.role.value,
        created_at=current_user.created_at.isoformat(),
        updated_at=current_user.updated_at.isoformat()
    )
    
    return success_response(user_data.dict())


@router.patch("/me")
async def update_current_user(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user information.
    
    Args:
        request: Update request with new username
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated user information
    """
    if request.username:
        # Check if username is already taken
        result = await db.execute(
            select(User).where(
                User.username == request.username,
                User.id != current_user.id
            )
        )
        if result.scalar_one_or_none():
            from app.core.exceptions import ConflictError
            raise ConflictError("Username already taken")
        
        current_user.username = request.username
    
    await db.commit()
    await db.refresh(current_user)
    
    user_data = UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        balance=float(current_user.balance),
        role=current_user.role.value,
        created_at=current_user.created_at.isoformat(),
        updated_at=current_user.updated_at.isoformat()
    )
    
    return success_response(user_data.dict(), "User updated successfully")


@router.post("/me/recharge")
async def recharge_balance(
    request: RechargeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Recharge user balance.
    
    Note: This is a placeholder. Actual payment integration will be implemented later.
    
    Args:
        request: Recharge request with amount and payment method
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Payment order information
    """
    # TODO: Implement actual payment integration
    # For now, just return a placeholder response
    
    recharge_data = RechargeResponse(
        order_id="placeholder-order-id",
        amount=request.amount,
        payment_url="https://payment.example.com/pay/placeholder",
        status="pending"
    )
    
    return success_response(recharge_data.dict(), "Recharge order created")
