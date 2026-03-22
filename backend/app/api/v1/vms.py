"""
Virtual Machine management API endpoints.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from app.infrastructure.database.base import get_db
from app.infrastructure.database.models import VM, Plan, User, VMStatus
from app.api.deps import get_current_active_user, get_pagination_params
from app.core.exceptions import NotFoundError, BadRequestError, InsufficientBalanceError, ForbiddenError
from app.core.response import success_response, paginated_response

router = APIRouter()


# Request/Response Models
class PlanResponse(BaseModel):
    """Plan response model."""
    id: str
    name: str
    description: Optional[str]
    cpu: int
    memory: int
    disk: int
    max_agents: int
    max_channels: int
    price_per_month: float
    features: List[str]
    
    class Config:
        from_attributes = True


class VMCreateRequest(BaseModel):
    """VM creation request."""
    name: str = Field(..., min_length=3, max_length=100)
    plan_id: str
    agent_template_id: Optional[str] = None
    region: Optional[str] = "default"


class VMResponse(BaseModel):
    """VM response model."""
    id: str
    name: str
    status: str
    ip_address: Optional[str]
    plan: PlanResponse
    created_at: str
    expires_at: str
    
    class Config:
        from_attributes = True


class VMDetailResponse(BaseModel):
    """VM detail response model."""
    id: str
    name: str
    status: str
    ip_address: Optional[str]
    plan: PlanResponse
    expires_at: str
    created_at: str
    updated_at: str
    usage: dict
    
    class Config:
        from_attributes = True


class VMListResponse(BaseModel):
    """VM list response with pagination."""
    items: List[VMResponse]
    total: int
    page: int
    page_size: int
    pages: int


class VMOperationResponse(BaseModel):
    """VM operation response."""
    id: str
    status: str
    message: str


class VMRenewRequest(BaseModel):
    """VM renewal request."""
    months: int = Field(..., ge=1, le=12)


# Plan endpoints
@router.get("/plans")
async def list_plans(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all available plans.
    
    Args:
        db: Database session
        
    Returns:
        List of available plans
    """
    result = await db.execute(
        select(Plan)
        .where(Plan.is_active == True)
        .order_by(Plan.sort_order)
    )
    plans = result.scalars().all()
    
    plans_data = [
        PlanResponse(
            id=str(plan.id),
            name=plan.name,
            description=plan.description,
            cpu=plan.cpu,
            memory=plan.memory,
            disk=plan.disk,
            max_agents=plan.max_agents,
            max_channels=plan.max_channels,
            price_per_month=float(plan.price_per_month),
            features=plan.features or []
        ).dict()
        for plan in plans
    ]
    
    return success_response(plans_data)


# VM endpoints
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_vm(
    request: VMCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new virtual machine.
    
    Args:
        request: VM creation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created VM information
        
    Raises:
        NotFoundError: If plan not found
        InsufficientBalanceError: If user has insufficient balance
    """
    # Get plan
    result = await db.execute(select(Plan).where(Plan.id == request.plan_id))
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise NotFoundError("Plan", request.plan_id)
    
    # Check user balance
    if current_user.balance < plan.price_per_month:
        raise InsufficientBalanceError(
            required=float(plan.price_per_month),
            available=float(current_user.balance)
        )
    
    # Check if VM name already exists for user
    result = await db.execute(
        select(VM).where(
            VM.user_id == current_user.id,
            VM.name == request.name
        )
    )
    if result.scalar_one_or_none():
        from app.core.exceptions import ConflictError
        raise ConflictError("VM with this name already exists")
    
    # Create VM record
    vm = VM(
        user_id=current_user.id,
        plan_id=plan.id,
        name=request.name,
        status=VMStatus.CREATING,
        cpu=plan.cpu,
        memory=plan.memory,
        disk=plan.disk,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    
    db.add(vm)
    
    # TODO: Deduct balance and create order
    # TODO: Trigger Libvirt VM creation
    # TODO: Deploy OpenClaw agent
    
    await db.commit()
    await db.refresh(vm)
    
    vm_data = VMResponse(
        id=str(vm.id),
        name=vm.name,
        status=vm.status.value,
        ip_address=str(vm.ip_address) if vm.ip_address else None,
        plan=PlanResponse(
            id=str(plan.id),
            name=plan.name,
            description=plan.description,
            cpu=plan.cpu,
            memory=plan.memory,
            disk=plan.disk,
            max_agents=plan.max_agents,
            max_channels=plan.max_channels,
            price_per_month=float(plan.price_per_month),
            features=plan.features or []
        ),
        created_at=vm.created_at.isoformat(),
        expires_at=vm.expires_at.isoformat()
    )
    
    return success_response(vm_data.dict(), "VM creation initiated")


@router.get("")
async def list_vms(
    status_filter: Optional[str] = None,
    pagination: tuple = Depends(get_pagination_params),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user's virtual machines.
    
    Args:
        status_filter: Optional status filter
        pagination: Pagination parameters
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of VMs with pagination
    """
    skip, limit = pagination
    
    # Build query
    query = select(VM).where(VM.user_id == current_user.id)
    
    if status_filter:
        query = query.where(VM.status == status_filter)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(VM.created_at.desc())
    result = await db.execute(query)
    vms = result.scalars().all()
    
    # Build response
    items = []
    for vm in vms:
        # Get plan
        plan_result = await db.execute(select(Plan).where(Plan.id == vm.plan_id))
        plan = plan_result.scalar_one()
        
        items.append(VMResponse(
            id=str(vm.id),
            name=vm.name,
            status=vm.status.value,
            ip_address=str(vm.ip_address) if vm.ip_address else None,
            plan=PlanResponse(
                id=str(plan.id),
                name=plan.name,
                description=plan.description,
                cpu=plan.cpu,
                memory=plan.memory,
                disk=plan.disk,
                max_agents=plan.max_agents,
                max_channels=plan.max_channels,
                price_per_month=float(plan.price_per_month),
                features=plan.features or []
            ),
            created_at=vm.created_at.isoformat(),
            expires_at=vm.expires_at.isoformat()
        ).dict())
    
    page = (skip // limit) + 1 if limit > 0 else 1
    return paginated_response(items, total, page, limit)


@router.get("/{vm_id}")
async def get_vm(
    vm_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get VM details.
    
    Args:
        vm_id: VM ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        VM details
        
    Raises:
        NotFoundError: If VM not found
        ForbiddenError: If VM doesn't belong to user
    """
    result = await db.execute(select(VM).where(VM.id == vm_id))
    vm = result.scalar_one_or_none()
    
    if not vm:
        raise NotFoundError("VM", vm_id)
    
    if vm.user_id != current_user.id:
        raise ForbiddenError("You don't have access to this VM")
    
    # Get plan
    plan_result = await db.execute(select(Plan).where(Plan.id == vm.plan_id))
    plan = plan_result.scalar_one()
    
    # TODO: Get real usage data from Libvirt
    usage = {
        "cpu_percent": 0.0,
        "memory_percent": 0.0,
        "disk_percent": 0.0,
        "network_in_bytes": 0,
        "network_out_bytes": 0
    }
    
    vm_data = VMDetailResponse(
        id=str(vm.id),
        name=vm.name,
        status=vm.status.value,
        ip_address=str(vm.ip_address) if vm.ip_address else None,
        plan=PlanResponse(
            id=str(plan.id),
            name=plan.name,
            description=plan.description,
            cpu=plan.cpu,
            memory=plan.memory,
            disk=plan.disk,
            max_agents=plan.max_agents,
            max_channels=plan.max_channels,
            price_per_month=float(plan.price_per_month),
            features=plan.features or []
        ),
        expires_at=vm.expires_at.isoformat(),
        created_at=vm.created_at.isoformat(),
        updated_at=vm.updated_at.isoformat(),
        usage=usage
    )
    
    return success_response(vm_data.dict())


@router.post("/{vm_id}/start")
async def start_vm(
    vm_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start a VM.
    
    Args:
        vm_id: VM ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Operation status
    """
    result = await db.execute(select(VM).where(VM.id == vm_id))
    vm = result.scalar_one_or_none()
    
    if not vm:
        raise NotFoundError("VM", vm_id)
    
    if vm.user_id != current_user.id:
        raise ForbiddenError("You don't have access to this VM")
    
    # TODO: Implement Libvirt start operation
    
    operation_data = VMOperationResponse(
        id=str(vm.id),
        status="starting",
        message="虚拟机正在启动"
    )
    
    return success_response(operation_data.dict(), "VM start operation initiated")


@router.post("/{vm_id}/stop")
async def stop_vm(
    vm_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stop a VM.
    
    Args:
        vm_id: VM ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Operation status
    """
    result = await db.execute(select(VM).where(VM.id == vm_id))
    vm = result.scalar_one_or_none()
    
    if not vm:
        raise NotFoundError("VM", vm_id)
    
    if vm.user_id != current_user.id:
        raise ForbiddenError("You don't have access to this VM")
    
    # TODO: Implement Libvirt stop operation
    
    operation_data = VMOperationResponse(
        id=str(vm.id),
        status="stopping",
        message="虚拟机正在停止"
    )
    
    return success_response(operation_data.dict(), "VM stop operation initiated")


@router.delete("/{vm_id}")
async def delete_vm(
    vm_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a VM.
    
    Args:
        vm_id: VM ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Operation status
    """
    result = await db.execute(select(VM).where(VM.id == vm_id))
    vm = result.scalar_one_or_none()
    
    if not vm:
        raise NotFoundError("VM", vm_id)
    
    if vm.user_id != current_user.id:
        raise ForbiddenError("You don't have access to this VM")
    
    # TODO: Implement Libvirt delete operation
    
    operation_data = VMOperationResponse(
        id=str(vm.id),
        status="deleting",
        message="虚拟机正在删除，所有数据将被清除"
    )
    
    return success_response(operation_data.dict(), "VM deletion initiated")


@router.post("/{vm_id}/renew")
async def renew_vm(
    vm_id: str,
    request: VMRenewRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Renew a VM subscription.
    
    Args:
        vm_id: VM ID
        request: Renewal request with number of months
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Renewal information
    """
    result = await db.execute(select(VM).where(VM.id == vm_id))
    vm = result.scalar_one_or_none()
    
    if not vm:
        raise NotFoundError("VM", vm_id)
    
    if vm.user_id != current_user.id:
        raise ForbiddenError("You don't have access to this VM")
    
    # Get plan
    plan_result = await db.execute(select(Plan).where(Plan.id == vm.plan_id))
    plan = plan_result.scalar_one()
    
    # Calculate cost
    cost = float(plan.price_per_month) * request.months
    
    # Check balance
    if current_user.balance < cost:
        raise InsufficientBalanceError(required=cost, available=float(current_user.balance))
    
    # TODO: Deduct balance and update expiration date
    
    renewal_data = {
        "id": str(vm.id),
        "expires_at": (vm.expires_at + timedelta(days=30 * request.months)).isoformat(),
        "cost": cost,
        "new_balance": float(current_user.balance) - cost
    }
    
    return success_response(renewal_data, "VM renewed successfully")
