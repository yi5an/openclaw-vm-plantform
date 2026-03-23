"""
Billing management API endpoints.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import StatementError, DataError
from pydantic import BaseModel, Field, ConfigDict
from app.infrastructure.database.base import get_db
from app.infrastructure.database.models import (
    Order, TokenUsage, User, Agent, VM, 
    OrderType, OrderStatus
)
from app.api.deps import get_current_active_user, get_pagination_params
from app.core.exceptions import NotFoundError, BadRequestError, ForbiddenError
from app.core.response import success_response, paginated_response

router = APIRouter()


# ==================== Request/Response Models ====================

class UsageQueryRequest(BaseModel):
    """Usage query parameters."""
    start_date: Optional[datetime] = Field(None, description="Start date for query")
    end_date: Optional[datetime] = Field(None, description="End date for query")
    agent_id: Optional[str] = Field(None, description="Filter by agent ID")


class UsageRecord(BaseModel):
    """Single usage record."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    agent_id: str
    agent_name: Optional[str] = None
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    created_at: datetime


class UsageStatsResponse(BaseModel):
    """Usage statistics response."""
    total_tokens: int
    total_cost: float
    by_agent: List[dict]
    by_model: List[dict]


class BalanceResponse(BaseModel):
    """Balance response."""
    balance: float
    pending: float
    total_recharged: float
    total_used: float


class OrderResponse(BaseModel):
    """Order response model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    type: str
    amount: float
    balance_before: float
    balance_after: float
    description: Optional[str] = None
    status: str
    payment_method: Optional[str] = None
    created_at: datetime


class RechargeRequest(BaseModel):
    """Recharge request."""
    amount: float = Field(..., gt=0, description="Recharge amount")
    payment_method: str = Field(..., description="Payment method: alipay, wechat, etc.")


class RechargeResponse(BaseModel):
    """Recharge response."""
    order_id: str
    amount: float
    balance_before: float
    balance_after: float
    status: str
    payment_url: Optional[str] = None  # Mock payment URL


# ==================== Helper Functions ====================

async def get_period_range(period: str) -> tuple[datetime, datetime]:
    """
    Get date range for a given period.
    
    Args:
        period: day, week, or month
        
    Returns:
        Tuple of (start_date, end_date)
    """
    now = datetime.utcnow()
    
    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "week":
        start = now - timedelta(days=7)
        end = now
    elif period == "month":
        start = now - timedelta(days=30)
        end = now
    else:
        raise BadRequestError(f"Invalid period: {period}. Must be 'day', 'week', or 'month'")
    
    return start, end


# ==================== API Endpoints ====================

@router.get("/usage")
async def get_usage_records(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get token usage records for the current user.
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        agent_id: Optional agent ID filter
        page: Page number (1-indexed)
        page_size: Number of items per page
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Paginated list of usage records
    """
    # Build query with filters
    query = select(TokenUsage).where(TokenUsage.user_id == current_user.id)
    
    # Apply date filters
    if start_date:
        query = query.where(TokenUsage.created_at >= start_date)
    if end_date:
        query = query.where(TokenUsage.created_at <= end_date)
    
    # Apply agent filter
    if agent_id:
        try:
            agent_uuid = UUID(agent_id)
            query = query.where(TokenUsage.agent_id == agent_uuid)
        except ValueError:
            raise BadRequestError("Invalid agent ID format")
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    skip = (page - 1) * page_size
    query = query.order_by(TokenUsage.created_at.desc()).offset(skip).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    usage_records = result.scalars().all()
    
    # Get agent names in batch (avoid N+1)
    agent_ids = list(set(record.agent_id for record in usage_records))
    agent_query = select(Agent.id, Agent.name).where(Agent.id.in_(agent_ids))
    agent_result = await db.execute(agent_query)
    agent_map = {str(agent.id): agent.name for agent in agent_result.all()}
    
    # Format response
    items = []
    for record in usage_records:
        items.append({
            "id": str(record.id),
            "agent_id": str(record.agent_id),
            "agent_name": agent_map.get(str(record.agent_id)),
            "model": record.model,
            "prompt_tokens": record.prompt_tokens,
            "completion_tokens": record.completion_tokens,
            "total_tokens": record.total_tokens,
            "cost": float(record.cost),
            "created_at": record.created_at.isoformat()
        })
    
    return paginated_response(items, total, page, page_size)


@router.get("/stats")
async def get_usage_stats(
    period: str = Query("month", pattern="^(day|week|month)$", description="Time period"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get usage statistics for the current user.
    
    Args:
        period: Time period (day, week, month)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Usage statistics grouped by agent and model
    """
    # Get date range
    start_date, end_date = await get_period_range(period)
    
    # Query total stats
    total_query = select(
        func.sum(TokenUsage.total_tokens).label("total_tokens"),
        func.sum(TokenUsage.cost).label("total_cost")
    ).where(
        and_(
            TokenUsage.user_id == current_user.id,
            TokenUsage.created_at >= start_date,
            TokenUsage.created_at <= end_date
        )
    )
    
    total_result = await db.execute(total_query)
    total_stats = total_result.one()
    
    total_tokens = total_stats.total_tokens or 0
    total_cost = float(total_stats.total_cost or 0)
    
    # Query stats by agent (with agent names in one query)
    by_agent_query = select(
        TokenUsage.agent_id,
        Agent.name.label("agent_name"),
        func.sum(TokenUsage.total_tokens).label("tokens"),
        func.sum(TokenUsage.cost).label("cost")
    ).join(
        Agent, TokenUsage.agent_id == Agent.id
    ).where(
        and_(
            TokenUsage.user_id == current_user.id,
            TokenUsage.created_at >= start_date,
            TokenUsage.created_at <= end_date
        )
    ).group_by(TokenUsage.agent_id, Agent.name).order_by(func.sum(TokenUsage.cost).desc())
    
    by_agent_result = await db.execute(by_agent_query)
    by_agent = [
        {
            "agent_id": str(row.agent_id),
            "agent_name": row.agent_name,
            "tokens": row.tokens,
            "cost": float(row.cost)
        }
        for row in by_agent_result.all()
    ]
    
    # Query stats by model
    by_model_query = select(
        TokenUsage.model,
        func.sum(TokenUsage.total_tokens).label("tokens"),
        func.sum(TokenUsage.cost).label("cost")
    ).where(
        and_(
            TokenUsage.user_id == current_user.id,
            TokenUsage.created_at >= start_date,
            TokenUsage.created_at <= end_date
        )
    ).group_by(TokenUsage.model).order_by(func.sum(TokenUsage.cost).desc())
    
    by_model_result = await db.execute(by_model_query)
    by_model = [
        {
            "model": row.model,
            "tokens": row.tokens,
            "cost": float(row.cost)
        }
        for row in by_model_result.all()
    ]
    
    return success_response({
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "by_agent": by_agent,
        "by_model": by_model,
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    })


@router.get("/balance")
async def get_balance(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's balance information.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Balance information including current balance, pending, total recharged, and total used
    """
    # Get current balance
    balance = float(current_user.balance)
    
    # Calculate total recharged
    recharge_query = select(
        func.sum(Order.amount).label("total_recharged")
    ).where(
        and_(
            Order.user_id == current_user.id,
            Order.type == OrderType.RECHARGE,
            Order.status == OrderStatus.COMPLETED
        )
    )
    
    recharge_result = await db.execute(recharge_query)
    total_recharged = float(recharge_result.scalar() or 0)
    
    # Calculate total used (from token usage)
    usage_query = select(
        func.sum(TokenUsage.cost).label("total_used")
    ).where(TokenUsage.user_id == current_user.id)
    
    usage_result = await db.execute(usage_query)
    total_used = float(usage_result.scalar() or 0)
    
    # Calculate pending balance (recharges in pending status)
    pending_query = select(
        func.sum(Order.amount).label("pending")
    ).where(
        and_(
            Order.user_id == current_user.id,
            Order.type == OrderType.RECHARGE,
            Order.status == OrderStatus.PENDING
        )
    )
    
    pending_result = await db.execute(pending_query)
    pending = float(pending_result.scalar() or 0)
    
    return success_response({
        "balance": balance,
        "pending": pending,
        "total_recharged": total_recharged,
        "total_used": total_used
    })


@router.get("/orders")
async def get_orders(
    order_type: Optional[str] = Query(None, description="Filter by order type"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get order history for the current user.
    
    Args:
        order_type: Optional order type filter
        status: Optional order status filter
        page: Page number (1-indexed)
        page_size: Number of items per page
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Paginated list of orders
    """
    # Build query
    query = select(Order).where(Order.user_id == current_user.id)
    
    # Apply filters
    if order_type:
        try:
            order_type_enum = OrderType(order_type)
            query = query.where(Order.type == order_type_enum)
        except ValueError:
            raise BadRequestError(f"Invalid order type: {order_type}")
    
    if status:
        try:
            status_enum = OrderStatus(status)
            query = query.where(Order.status == status_enum)
        except ValueError:
            raise BadRequestError(f"Invalid order status: {status}")
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    skip = (page - 1) * page_size
    query = query.order_by(Order.created_at.desc()).offset(skip).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    orders = result.scalars().all()
    
    # Format response
    items = []
    for order in orders:
        items.append({
            "id": str(order.id),
            "type": order.type.value,
            "amount": float(order.amount),
            "balance_before": float(order.balance_before),
            "balance_after": float(order.balance_after),
            "description": order.description,
            "status": order.status.value,
            "payment_method": order.payment_method,
            "created_at": order.created_at.isoformat()
        })
    
    return paginated_response(items, total, page, page_size)


@router.post("/recharge")
async def create_recharge(
    request: RechargeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a recharge order.
    
    Args:
        request: Recharge request with amount and payment method
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Recharge order details with payment URL
    """
    # Validate payment method
    valid_payment_methods = ["alipay", "wechat", "bank_transfer"]
    if request.payment_method not in valid_payment_methods:
        raise BadRequestError(f"Invalid payment method. Must be one of: {', '.join(valid_payment_methods)}")
    
    # Get current balance
    balance_before = current_user.balance
    
    # Create order (in pending status)
    order = Order(
        user_id=current_user.id,
        type=OrderType.RECHARGE,
        amount=Decimal(str(request.amount)),
        balance_before=balance_before,
        balance_after=balance_before,  # Will be updated after payment
        description=f"Account recharge via {request.payment_method}",
        status=OrderStatus.PENDING,
        payment_method=request.payment_method
    )
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    # Mock: Simulate instant payment completion
    # In production, this would redirect to payment gateway
    balance_after = balance_before + Decimal(str(request.amount))
    current_user.balance = balance_after
    order.balance_after = balance_after
    order.status = OrderStatus.COMPLETED
    order.payment_transaction_id = f"MOCK_{datetime.utcnow().timestamp()}"
    
    await db.commit()
    await db.refresh(order)
    
    # Mock payment URL (in production, this would be a real payment gateway URL)
    payment_url = f"https://payment.example.com/pay/{order.id}"
    
    return success_response({
        "order_id": str(order.id),
        "amount": float(order.amount),
        "balance_before": float(balance_before),
        "balance_after": float(balance_after),
        "status": order.status.value,
        "payment_url": payment_url,
        "payment_method": request.payment_method
    }, "Recharge order created successfully")
