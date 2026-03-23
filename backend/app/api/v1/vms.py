"""
Virtual Machine management API endpoints.
"""
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from app.infrastructure.database.base import get_db
from app.infrastructure.database.models import VM, Plan, User, VMStatus
from app.api.deps import get_current_active_user, get_pagination_params
from app.core.exceptions import NotFoundError, BadRequestError, InsufficientBalanceError, ForbiddenError, VMOperationError
from app.core.response import success_response, paginated_response
from app.infrastructure.vm.libvirt_manager import libvirt_manager, VMSpec
from app.infrastructure.vm.ssh_deployer import ssh_deployer, DeployConfig

logger = logging.getLogger(__name__)
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


# VM Provisioning Task (Background)
async def provision_vm_task(
    vm_id: str,
    vm_name: str,
    cpu: int,
    memory: int,
    disk: int,
    user_id: str,
    db_url: str
):
    """
    Background task for VM provisioning.
    
    Steps:
    1. Create VM in Libvirt
    2. Start VM
    3. Wait for IP assignment
    4. Deploy OpenClaw via SSH
    5. Update VM status in database
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    logger.info(f"[VM Provisioning] Starting for VM {vm_id}")
    
    # Create database session
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Get VM record
            result = await db.execute(select(VM).where(VM.id == vm_id))
            vm = result.scalar_one_or_none()
            
            if not vm:
                logger.error(f"[VM Provisioning] VM {vm_id} not found in database")
                return
            
            # Step 1: Create VM in Libvirt
            logger.info(f"[VM Provisioning] Step 1/5: Creating VM in Libvirt")
            spec = VMSpec(
                name=vm_name,
                cpu=cpu,
                memory=memory,
                disk=disk,
                cloud_init_config={
                    "hostname": vm_name,
                    "users": [{
                        "name": "root",
                        "ssh_authorized_keys": []  # TODO: 从配置获取
                    }]
                }
            )
            
            vm_info = await libvirt_manager.create_vm(spec)
            vm.libvirt_domain_name = vm_info.name
            await db.commit()
            
            logger.info(f"[VM Provisioning] VM created in Libvirt: {vm_info.id}")
            
            # Step 2: Start VM
            logger.info(f"[VM Provisioning] Step 2/5: Starting VM")
            await libvirt_manager.start_vm(vm_info.id)
            
            vm.status = VMStatus.RUNNING
            vm.last_start_at = datetime.utcnow()
            await db.commit()
            
            logger.info(f"[VM Provisioning] VM started successfully")
            
            # Step 3: Wait for IP assignment (max 60 seconds)
            logger.info(f"[VM Provisioning] Step 3/5: Waiting for IP assignment")
            ip_address = None
            for attempt in range(12):  # 12 * 5s = 60s
                try:
                    await asyncio.sleep(5)
                    ip_address = await libvirt_manager.get_vm_ip(vm_info.id)
                    if ip_address:
                        break
                except Exception as e:
                    logger.warning(f"[VM Provisioning] IP attempt {attempt + 1} failed: {e}")
            
            if not ip_address:
                raise Exception("Failed to get VM IP address after 60 seconds")
            
            vm.ip_address = ip_address
            await db.commit()
            
            logger.info(f"[VM Provisioning] IP assigned: {ip_address}")
            
            # Step 4: Deploy OpenClaw via SSH
            logger.info(f"[VM Provisioning] Step 4/5: Deploying OpenClaw")
            
            # Wait for SSH to be ready
            await asyncio.sleep(10)
            
            deploy_config = DeployConfig(
                agents=[],
                openclaw_version="latest",
                install_docker=True
            )
            
            deploy_result = await ssh_deployer.deploy_openclaw(
                host=ip_address,
                config=deploy_config
            )
            
            if deploy_result["status"] != "success":
                raise Exception(f"OpenClaw deployment failed: {deploy_result.get('error')}")
            
            logger.info(f"[VM Provisioning] OpenClaw deployed successfully")
            
            # Step 5: Verify deployment
            logger.info(f"[VM Provisioning] Step 5/5: Verifying deployment")
            
            health = await ssh_deployer.check_openclaw_health(ip_address)
            if not health["is_healthy"]:
                logger.warning(f"[VM Provisioning] Health check failed, but VM is running")
            
            logger.info(f"[VM Provisioning] ✅ VM {vm_id} provisioning completed successfully")
            
        except Exception as e:
            logger.error(f"[VM Provisioning] ❌ Failed to provision VM {vm_id}: {e}")
            
            # Update VM status to ERROR
            try:
                result = await db.execute(select(VM).where(VM.id == vm_id))
                vm = result.scalar_one_or_none()
                if vm:
                    vm.status = VMStatus.ERROR
                    await db.commit()
            except Exception as db_error:
                logger.error(f"[VM Provisioning] Failed to update VM status: {db_error}")


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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new virtual machine.
    
    Args:
        request: VM creation request
        background_tasks: FastAPI background tasks
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
    
    await db.commit()
    await db.refresh(vm)
    
    # Start background provisioning task
    from app.core.config import settings
    
    background_tasks.add_task(
        provision_vm_task,
        str(vm.id),
        vm.name,
        vm.cpu,
        vm.memory,
        vm.disk,
        str(current_user.id),
        settings.DATABASE_URL
    )
    
    logger.info(f"VM creation initiated: {vm.id} (user: {current_user.id})")
    
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
    
    return success_response(vm_data.dict(), "VM creation initiated. Provisioning in background.")


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
    
    # Get real usage data from Libvirt
    usage = {
        "cpu_percent": 0.0,
        "memory_percent": 0.0,
        "disk_percent": 0.0,
        "network_in_bytes": 0,
        "network_out_bytes": 0
    }
    
    try:
        if vm.libvirt_domain_name and vm.status == VMStatus.RUNNING:
            vm_status = await libvirt_manager.get_vm_status(str(vm.id))
            usage["cpu_percent"] = vm_status["cpu_percent"]
            usage["memory_percent"] = vm_status["memory_percent"]
            # TODO: Add disk and network metrics
    except Exception as e:
        logger.warning(f"Failed to get VM usage data: {e}")
    
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
    
    if vm.status == VMStatus.STOPPED:
        raise BadRequestError("VM is already stopped")
    
    try:
        # Call Libvirt to stop VM
        if vm.libvirt_domain_name:
            await libvirt_manager.stop_vm(str(vm.id))
        
        # Update database status
        vm.status = VMStatus.STOPPED
        vm.last_stop_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"VM {vm_id} stopped successfully")
        
        operation_data = VMOperationResponse(
            id=str(vm.id),
            status="stopped",
            message="虚拟机已停止"
        )
        
        return success_response(operation_data.dict(), "VM stopped successfully")
        
    except Exception as e:
        logger.error(f"Failed to stop VM {vm_id}: {e}")
        raise VMOperationError("stop", str(e))


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
