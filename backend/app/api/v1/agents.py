"""
Agent management API endpoints.
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import StatementError, DataError
from pydantic import BaseModel, Field, ConfigDict
from app.infrastructure.database.base import get_db
from app.infrastructure.database.models import Agent, VM, Plan, AgentTemplate, AgentStatus
from app.api.deps import get_current_active_user, get_pagination_params
from app.core.exceptions import NotFoundError, BadRequestError, ForbiddenError, ConflictError
from app.core.response import success_response, paginated_response

router = APIRouter()


# Request/Response Models
class ModelConfig(BaseModel):
    """Model configuration."""
    provider: str = Field(..., description="platform or custom")
    model_name: str = Field(..., description="Model name")
    api_key: Optional[str] = Field(None, description="API key for custom provider")
    temperature: float = Field(0.7, ge=0, le=2, description="Temperature setting")


class AgentCreateRequest(BaseModel):
    """Agent creation request."""
    vm_id: str = Field(..., description="VM ID")
    template_id: Optional[str] = Field(None, description="Template ID (optional)")
    name: str = Field(..., min_length=3, max_length=100, description="Agent name")
    system_prompt: str = Field(..., description="System prompt for the agent")
    llm_config: ModelConfig = Field(..., description="Model configuration")


class AgentUpdateRequest(BaseModel):
    """Agent update request."""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    system_prompt: Optional[str] = None
    llm_config: Optional[ModelConfig] = None


class AgentResponse(BaseModel):
    """Agent response model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    vm_id: str
    template_id: Optional[str]
    name: str
    status: str
    system_prompt: Optional[str]
    agent_model_config: dict
    messages_count: int
    last_active_at: Optional[str]
    created_at: str
    updated_at: str


class TokenValidationRequest(BaseModel):
    """Token validation request."""
    provider: str = Field(..., description="Provider name (e.g., openai, anthropic)")
    api_key: str = Field(..., description="API key to validate")
    model_name: str = Field(..., description="Model name to test")


class TokenValidationResponse(BaseModel):
    """Token validation response."""
    valid: bool
    provider: str
    model_name: str
    message: str


# Helper functions
def validate_uuid(resource_id: str, resource_name: str = "Resource") -> UUID:
    """
    Validate that a string is a valid UUID.
    
    Args:
        resource_id: String to validate
        resource_name: Name of the resource for error message
        
    Returns:
        UUID object if valid
        
    Raises:
        NotFoundError: If string is not a valid UUID
    """
    try:
        return UUID(resource_id)
    except (ValueError, AttributeError, TypeError):
        # Invalid UUID format - treat as not found (don't leak implementation details)
        raise NotFoundError(resource_name, resource_id)


async def verify_vm_ownership(vm_id: str, user_id: str, db: AsyncSession) -> VM:
    """
    Verify that VM belongs to the user.
    
    Args:
        vm_id: VM ID
        user_id: User ID
        db: Database session
        
    Returns:
        VM object
        
    Raises:
        NotFoundError: If VM not found
        ForbiddenError: If VM doesn't belong to user
    """
    result = await db.execute(select(VM).where(VM.id == vm_id))
    vm = result.scalar_one_or_none()
    
    if not vm:
        raise NotFoundError("VM", vm_id)
    
    if str(vm.user_id) != user_id:
        raise ForbiddenError("You don't have access to this VM")
    
    return vm


async def check_agent_quota(vm: VM, db: AsyncSession) -> None:
    """
    Check if VM can create more agents based on plan limits.
    
    Args:
        vm: VM object
        db: Database session
        
    Raises:
        BadRequestError: If quota exceeded
    """
    # Get plan
    result = await db.execute(select(Plan).where(Plan.id == vm.plan_id))
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise BadRequestError("Plan not found for this VM")
    
    # Count current agents
    count_result = await db.execute(
        select(func.count()).select_from(Agent).where(Agent.vm_id == vm.id)
    )
    current_count = count_result.scalar()
    
    if current_count >= plan.max_agents:
        raise BadRequestError(
            f"Agent quota exceeded. Your plan allows {plan.max_agents} agents per VM. "
            f"Current: {current_count}"
        )


# API Endpoints

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: AgentCreateRequest,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new agent.
    
    Args:
        request: Agent creation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created agent information
        
    Raises:
        NotFoundError: If VM or template not found
        ForbiddenError: If VM doesn't belong to user
        BadRequestError: If quota exceeded
    """
    # Validate UUID format
    validate_uuid(request.vm_id, "VM")
    if request.template_id:
        validate_uuid(request.template_id, "Agent Template")
    
    # Verify VM ownership
    vm = await verify_vm_ownership(request.vm_id, str(current_user.id), db)
    
    # Check quota
    await check_agent_quota(vm, db)
    
    # Verify template if provided
    template = None
    if request.template_id:
        result = await db.execute(
            select(AgentTemplate).where(AgentTemplate.id == request.template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            raise NotFoundError("Agent Template", request.template_id)
    
    # Validate custom API key
    if request.llm_config.provider == "custom":
        if not request.llm_config.api_key:
            raise BadRequestError("API key is required for custom provider")
    
    # Create agent
    agent = Agent(
        vm_id=vm.id,
        template_id=template.id if template else None,
        name=request.name,
        status=AgentStatus.CREATING,
        system_prompt=request.system_prompt,
        model_config=request.llm_config.dict(),
        messages_count=0
    )
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    agent_data = AgentResponse(
        id=str(agent.id),
        vm_id=str(agent.vm_id),
        template_id=str(agent.template_id) if agent.template_id else None,
        name=agent.name,
        status=agent.status.value,
        system_prompt=agent.system_prompt,
        agent_model_config=agent.model_config,
        messages_count=agent.messages_count,
        last_active_at=agent.last_active_at.isoformat() if agent.last_active_at else None,
        created_at=agent.created_at.isoformat(),
        updated_at=agent.updated_at.isoformat()
    )
    
    return success_response(agent_data.dict(), "Agent created successfully")


@router.get("")
async def list_agents(
    vm_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    pagination: tuple = Depends(get_pagination_params),
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List agents.
    
    Args:
        vm_id: Optional VM ID filter
        status_filter: Optional status filter
        pagination: Pagination parameters
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of agents with pagination
    """
    skip, limit = pagination
    
    # Build query - join with VM to filter by user
    query = (
        select(Agent)
        .join(VM)
        .where(VM.user_id == current_user.id)
    )
    
    if vm_id:
        # Validate UUID format
        validate_uuid(vm_id, "VM")
        # Verify VM ownership
        await verify_vm_ownership(vm_id, str(current_user.id), db)
        query = query.where(Agent.vm_id == vm_id)
    
    if status_filter:
        query = query.where(Agent.status == status_filter)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(Agent.created_at.desc())
    result = await db.execute(query)
    agents = result.scalars().all()
    
    # Build response
    items = [
        AgentResponse(
            id=str(agent.id),
            vm_id=str(agent.vm_id),
            template_id=str(agent.template_id) if agent.template_id else None,
            name=agent.name,
            status=agent.status.value,
            system_prompt=agent.system_prompt,
            agent_model_config=agent.model_config,
            messages_count=agent.messages_count,
            last_active_at=agent.last_active_at.isoformat() if agent.last_active_at else None,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat()
        ).dict()
        for agent in agents
    ]
    
    page = (skip // limit) + 1 if limit > 0 else 1
    return paginated_response(items, total, page, limit)


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get agent details.
    
    Args:
        agent_id: Agent ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Agent details
        
    Raises:
        NotFoundError: If agent not found
        ForbiddenError: If agent's VM doesn't belong to user
    """
    # Validate UUID format
    validate_uuid(agent_id, "Agent")
    
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
    except (StatementError, DataError) as e:
        # Handle any database-level errors (e.g., invalid UUID format in query)
        raise NotFoundError("Agent", agent_id)
    
    if not agent:
        raise NotFoundError("Agent", agent_id)
    
    # Verify ownership through VM
    await verify_vm_ownership(str(agent.vm_id), str(current_user.id), db)
    
    agent_data = AgentResponse(
        id=str(agent.id),
        vm_id=str(agent.vm_id),
        template_id=str(agent.template_id) if agent.template_id else None,
        name=agent.name,
        status=agent.status.value,
        system_prompt=agent.system_prompt,
        agent_model_config=agent.model_config,
        messages_count=agent.messages_count,
        last_active_at=agent.last_active_at.isoformat() if agent.last_active_at else None,
        created_at=agent.created_at.isoformat(),
        updated_at=agent.updated_at.isoformat()
    )
    
    return success_response(agent_data.dict())


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str,
    request: AgentUpdateRequest,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update agent configuration.
    
    Args:
        agent_id: Agent ID
        request: Update request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated agent information
        
    Raises:
        NotFoundError: If agent not found
        ForbiddenError: If agent's VM doesn't belong to user
        BadRequestError: If trying to update running agent
    """
    # Validate UUID format
    validate_uuid(agent_id, "Agent")
    
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
    except (StatementError, DataError) as e:
        # Handle any database-level errors (e.g., invalid UUID format in query)
        raise NotFoundError("Agent", agent_id)
    
    if not agent:
        raise NotFoundError("Agent", agent_id)
    
    # Verify ownership through VM
    await verify_vm_ownership(str(agent.vm_id), str(current_user.id), db)
    
    # Check if agent is running (optional: might allow updates while running)
    # if agent.status == AgentStatus.RUNNING:
    #     raise BadRequestError("Cannot update running agent. Please stop it first.")
    
    # Update fields
    if request.name is not None:
        agent.name = request.name
    
    if request.system_prompt is not None:
        agent.system_prompt = request.system_prompt
    
    if request.llm_config is not None:
        # Validate custom API key if changing to custom provider
        if request.llm_config.provider == "custom":
            if not request.llm_config.api_key:
                raise BadRequestError("API key is required for custom provider")
        agent.model_config = request.llm_config.dict()
    
    agent.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(agent)
    
    agent_data = AgentResponse(
        id=str(agent.id),
        vm_id=str(agent.vm_id),
        template_id=str(agent.template_id) if agent.template_id else None,
        name=agent.name,
        status=agent.status.value,
        system_prompt=agent.system_prompt,
        agent_model_config=agent.model_config,
        messages_count=agent.messages_count,
        last_active_at=agent.last_active_at.isoformat() if agent.last_active_at else None,
        created_at=agent.created_at.isoformat(),
        updated_at=agent.updated_at.isoformat()
    )
    
    return success_response(agent_data.dict(), "Agent updated successfully")


@router.post("/{agent_id}/start")
async def start_agent(
    agent_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start an agent.
    
    Args:
        agent_id: Agent ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Operation status
        
    Raises:
        NotFoundError: If agent not found
        ForbiddenError: If agent's VM doesn't belong to user
        BadRequestError: If agent is already running or VM is not running
    """
    # Validate UUID format
    validate_uuid(agent_id, "Agent")
    
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
    except (StatementError, DataError) as e:
        # Handle any database-level errors (e.g., invalid UUID format in query)
        raise NotFoundError("Agent", agent_id)
    
    if not agent:
        raise NotFoundError("Agent", agent_id)
    
    # Verify ownership through VM
    vm = await verify_vm_ownership(str(agent.vm_id), str(current_user.id), db)
    
    # Check if VM is running
    if vm.status.value != "running":
        raise BadRequestError("Cannot start agent: VM is not running")
    
    # Check if agent is already running
    if agent.status == AgentStatus.RUNNING:
        raise BadRequestError("Agent is already running")
    
    # Update status
    agent.status = AgentStatus.RUNNING
    agent.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # TODO: Trigger actual agent startup process
    # This might involve:
    # - Initializing the AI model connection
    # - Setting up channels
    # - Starting background workers
    
    return success_response(
        {
            "id": str(agent.id),
            "status": agent.status.value,
            "message": "Agent started successfully"
        },
        "Agent start operation completed"
    )


@router.post("/{agent_id}/stop")
async def stop_agent(
    agent_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stop an agent.
    
    Args:
        agent_id: Agent ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Operation status
        
    Raises:
        NotFoundError: If agent not found
        ForbiddenError: If agent's VM doesn't belong to user
        BadRequestError: If agent is already stopped
    """
    # Validate UUID format
    validate_uuid(agent_id, "Agent")
    
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
    except (StatementError, DataError) as e:
        # Handle any database-level errors (e.g., invalid UUID format in query)
        raise NotFoundError("Agent", agent_id)
    
    if not agent:
        raise NotFoundError("Agent", agent_id)
    
    # Verify ownership through VM
    await verify_vm_ownership(str(agent.vm_id), str(current_user.id), db)
    
    # Check if agent is already stopped
    if agent.status == AgentStatus.STOPPED:
        raise BadRequestError("Agent is already stopped")
    
    # Update status
    agent.status = AgentStatus.STOPPED
    agent.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # TODO: Trigger actual agent shutdown process
    # This might involve:
    # - Closing active connections
    # - Flushing message queues
    # - Stopping background workers
    
    return success_response(
        {
            "id": str(agent.id),
            "status": agent.status.value,
            "message": "Agent stopped successfully"
        },
        "Agent stop operation completed"
    )


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an agent.
    
    Args:
        agent_id: Agent ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Operation status
        
    Raises:
        NotFoundError: If agent not found
        ForbiddenError: If agent's VM doesn't belong to user
        BadRequestError: If agent is running
    """
    # Validate UUID format
    validate_uuid(agent_id, "Agent")
    
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
    except (StatementError, DataError) as e:
        # Handle any database-level errors (e.g., invalid UUID format in query)
        raise NotFoundError("Agent", agent_id)
    
    if not agent:
        raise NotFoundError("Agent", agent_id)
    
    # Verify ownership through VM
    await verify_vm_ownership(str(agent.vm_id), str(current_user.id), db)
    
    # Check if agent is running
    if agent.status == AgentStatus.RUNNING:
        raise BadRequestError("Cannot delete running agent. Please stop it first.")
    
    # Delete agent (cascade delete will handle channels and token usages)
    try:
        await db.delete(agent)
        await db.commit()
    except (StatementError, DataError) as e:
        # Rollback on database errors
        await db.rollback()
        raise NotFoundError("Agent", agent_id)
    
    return success_response(
        {
            "id": agent_id,
            "message": "Agent deleted successfully"
        },
        "Agent deletion completed"
    )


@router.post("/validate-token")
async def validate_token(
    request: TokenValidationRequest,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate a custom API token.
    
    This endpoint tests if the provided API key is valid by making
    a test request to the provider's API.
    
    Args:
        request: Token validation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Validation result
    """
    # TODO: Implement actual token validation
    # This should:
    # 1. Route to the appropriate provider based on request.provider
    # 2. Make a lightweight API call (e.g., list models or minimal completion)
    # 3. Return success/failure based on response
    
    # For now, basic validation
    if not request.api_key or len(request.api_key) < 10:
        raise BadRequestError("Invalid API key format")
    
    # Simulate validation (replace with actual API call)
    # Example for OpenAI:
    # import openai
    # client = openai.OpenAI(api_key=request.api_key)
    # try:
    #     client.models.list()
    #     valid = True
    # except Exception as e:
    #     valid = False
    
    # Placeholder validation logic
    valid = True
    message = "Token validation successful"
    
    # Basic format checks
    if request.provider == "openai" and not request.api_key.startswith("sk-"):
        valid = False
        message = "Invalid OpenAI API key format"
    
    validation_result = TokenValidationResponse(
        valid=valid,
        provider=request.provider,
        model_name=request.model_name,
        message=message
    )
    
    return success_response(
        validation_result.dict(),
        message if valid else "Token validation failed"
    )
