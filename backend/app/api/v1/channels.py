"""
Channel management API endpoints.
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import StatementError, DataError
from pydantic import BaseModel, Field, ConfigDict, field_validator
import httpx
from app.infrastructure.database.base import get_db
from app.infrastructure.database.models import (
    Agent, Channel, ChannelType, ChannelStatus, AgentStatus
)
from app.api.deps import get_current_active_user, get_pagination_params
from app.core.exceptions import NotFoundError, BadRequestError, ForbiddenError, ConflictError
from app.core.response import success_response, paginated_response
from app.core.config import settings

router = APIRouter()


# Request/Response Models
class FeishuChannelConfig(BaseModel):
    """Feishu channel configuration."""
    app_id: str = Field(..., description="Feishu App ID (cli_xxx)")
    app_secret: str = Field(..., description="Feishu App Secret")
    
    @field_validator('app_id')
    @classmethod
    def validate_app_id(cls, v):
        if not v.startswith('cli_'):
            raise ValueError('Invalid Feishu App ID format (should start with cli_)')
        return v


class TelegramChannelConfig(BaseModel):
    """Telegram channel configuration."""
    bot_token: str = Field(..., description="Telegram Bot Token (123456:ABC)")
    allowed_chat_ids: List[int] = Field(..., description="List of allowed chat IDs")
    
    @field_validator('bot_token')
    @classmethod
    def validate_bot_token(cls, v):
        if ':' not in v or not v.split(':')[0].isdigit():
            raise ValueError('Invalid Telegram Bot Token format')
        return v


class FeishuChannelCreateRequest(BaseModel):
    """Feishu channel creation request."""
    agent_id: str = Field(..., description="Agent ID")
    config: FeishuChannelConfig = Field(..., description="Feishu configuration")


class TelegramChannelCreateRequest(BaseModel):
    """Telegram channel creation request."""
    agent_id: str = Field(..., description="Agent ID")
    config: TelegramChannelConfig = Field(..., description="Telegram configuration")


class ChannelResponse(BaseModel):
    """Channel response model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    agent_id: str
    type: str
    status: str
    config: dict
    configuration_steps: List[dict]
    test_message_sent: bool
    last_test_at: Optional[str]
    created_at: str
    updated_at: str


class ChannelStatusResponse(BaseModel):
    """Channel status check response."""
    channel_id: str
    type: str
    status: str
    is_connected: bool
    details: dict


class TestMessageRequest(BaseModel):
    """Test message request."""
    message: Optional[str] = Field("This is a test message from OpenClaw VM Platform", description="Custom test message")


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
        raise NotFoundError(resource_name, resource_id)


async def verify_agent_ownership(agent_id: str, user_id: str, db: AsyncSession) -> Agent:
    """
    Verify that agent belongs to the user.
    
    Args:
        agent_id: Agent ID
        user_id: User ID
        db: Database session
        
    Returns:
        Agent object
        
    Raises:
        NotFoundError: If agent not found
        ForbiddenError: If agent doesn't belong to user
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise NotFoundError("Agent", agent_id)
    
    # Verify ownership through VM
    from app.infrastructure.database.models import VM
    vm_result = await db.execute(select(VM).where(VM.id == agent.vm_id))
    vm = vm_result.scalar_one_or_none()
    
    if not vm or str(vm.user_id) != user_id:
        raise ForbiddenError("You don't have access to this agent")
    
    return agent


async def validate_feishu_credentials(app_id: str, app_secret: str) -> dict:
    """
    Validate Feishu app credentials by calling Feishu API.
    
    Args:
        app_id: Feishu App ID
        app_secret: Feishu App Secret
        
    Returns:
        Validation result with tenant_access_token if successful
        
    Raises:
        BadRequestError: If validation fails
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": app_id,
                    "app_secret": app_secret
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise BadRequestError("Failed to connect to Feishu API")
            
            data = response.json()
            
            if data.get("code") != 0:
                raise BadRequestError(f"Feishu validation failed: {data.get('msg', 'Unknown error')}")
            
            return {
                "valid": True,
                "tenant_access_token": data.get("tenant_access_token")
            }
        except httpx.TimeoutException:
            raise BadRequestError("Feishu API timeout - please try again")
        except Exception as e:
            raise BadRequestError(f"Feishu validation error: {str(e)}")


async def validate_telegram_bot_token(bot_token: str) -> dict:
    """
    Validate Telegram bot token by calling Telegram API.
    
    Args:
        bot_token: Telegram Bot Token
        
    Returns:
        Validation result with bot info if successful
        
    Raises:
        BadRequestError: If validation fails
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://api.telegram.org/bot{bot_token}/getMe",
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise BadRequestError("Failed to connect to Telegram API")
            
            data = response.json()
            
            if not data.get("ok"):
                raise BadRequestError(f"Telegram validation failed: {data.get('description', 'Unknown error')}")
            
            bot_info = data.get("result", {})
            return {
                "valid": True,
                "bot_id": bot_info.get("id"),
                "bot_username": bot_info.get("username"),
                "bot_name": bot_info.get("first_name")
            }
        except httpx.TimeoutException:
            raise BadRequestError("Telegram API timeout - please try again")
        except Exception as e:
            raise BadRequestError(f"Telegram validation error: {str(e)}")


def generate_webhook_url(channel_id: str, channel_type: str) -> str:
    """
    Generate webhook URL for channel.
    
    Args:
        channel_id: Channel ID
        channel_type: Channel type (feishu/telegram)
        
    Returns:
        Webhook URL
    """
    # TODO: Get base URL from settings
    base_url = getattr(settings, 'WEBHOOK_BASE_URL', 'https://your-domain.com')
    return f"{base_url}/webhooks/{channel_type}/{channel_id}"


def get_feishu_configuration_steps(channel_id: str) -> List[dict]:
    """
    Get configuration steps for Feishu channel.
    
    Args:
        channel_id: Channel ID
        
    Returns:
        List of configuration steps
    """
    webhook_url = generate_webhook_url(channel_id, "feishu")
    return [
        {
            "step": 1,
            "title": "Configure Event Subscription",
            "description": "Add the webhook URL to your Feishu app event subscription settings",
            "webhook_url": webhook_url,
            "completed": False
        },
        {
            "step": 2,
            "title": "Enable Events",
            "description": "Enable 'Receive Message' events in your Feishu app",
            "events": ["im.message.receive_v1"],
            "completed": False
        },
        {
            "step": 3,
            "title": "Test Connection",
            "description": "Send a test message to verify the integration",
            "completed": False
        }
    ]


def get_telegram_configuration_steps(channel_id: str) -> List[dict]:
    """
    Get configuration steps for Telegram channel.
    
    Args:
        channel_id: Channel ID
        
    Returns:
        List of configuration steps
    """
    webhook_url = generate_webhook_url(channel_id, "telegram")
    return [
        {
            "step": 1,
            "title": "Set Webhook",
            "description": "Configure the webhook URL for your Telegram bot",
            "webhook_url": webhook_url,
            "completed": False
        },
        {
            "step": 2,
            "title": "Configure Allowed Chats",
            "description": "Add chat IDs that are allowed to interact with the bot",
            "completed": False
        },
        {
            "step": 3,
            "title": "Test Bot",
            "description": "Send a test message to verify the bot is working",
            "completed": False
        }
    ]


# API Endpoints

@router.post("/feishu", status_code=status.HTTP_201_CREATED)
async def create_feishu_channel(
    request: FeishuChannelCreateRequest,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Configure Feishu channel for an agent.
    
    Args:
        request: Feishu channel creation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created channel information with configuration steps
        
    Raises:
        NotFoundError: If agent not found
        ForbiddenError: If agent doesn't belong to user
        BadRequestError: If Feishu credentials are invalid
    """
    # Validate UUID format
    validate_uuid(request.agent_id, "Agent")
    
    # Verify agent ownership
    agent = await verify_agent_ownership(request.agent_id, str(current_user.id), db)
    
    # Check if agent already has a Feishu channel
    existing = await db.execute(
        select(Channel).where(
            Channel.agent_id == agent.id,
            Channel.type == ChannelType.FEISHU
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("Agent already has a Feishu channel configured")
    
    # Validate Feishu credentials
    validation_result = await validate_feishu_credentials(
        request.config.app_id,
        request.config.app_secret
    )
    
    # Create channel
    channel = Channel(
        agent_id=agent.id,
        type=ChannelType.FEISHU,
        status=ChannelStatus.CONFIGURING,
        config={
            "app_id": request.config.app_id,
            "app_secret": request.config.app_secret,  # TODO: Encrypt in production
            "validated": True
        },
        configuration_steps=[]
    )
    
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    
    # Generate configuration steps
    config_steps = get_feishu_configuration_steps(str(channel.id))
    channel.configuration_steps = config_steps
    await db.commit()
    await db.refresh(channel)
    
    channel_data = ChannelResponse(
        id=str(channel.id),
        agent_id=str(channel.agent_id),
        type=channel.type.value,
        status=channel.status.value,
        config={k: v for k, v in channel.config.items() if k != 'app_secret'},  # Don't expose secret
        configuration_steps=channel.configuration_steps,
        test_message_sent=channel.test_message_sent,
        last_test_at=channel.last_test_at.isoformat() if channel.last_test_at else None,
        created_at=channel.created_at.isoformat(),
        updated_at=channel.updated_at.isoformat()
    )
    
    return success_response(
        channel_data.dict(),
        "Feishu channel created successfully. Please follow the configuration steps."
    )


@router.post("/telegram", status_code=status.HTTP_201_CREATED)
async def create_telegram_channel(
    request: TelegramChannelCreateRequest,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Configure Telegram channel for an agent.
    
    Args:
        request: Telegram channel creation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created channel information with configuration steps
        
    Raises:
        NotFoundError: If agent not found
        ForbiddenError: If agent doesn't belong to user
        BadRequestError: If Telegram credentials are invalid
    """
    # Validate UUID format
    validate_uuid(request.agent_id, "Agent")
    
    # Verify agent ownership
    agent = await verify_agent_ownership(request.agent_id, str(current_user.id), db)
    
    # Check if agent already has a Telegram channel
    existing = await db.execute(
        select(Channel).where(
            Channel.agent_id == agent.id,
            Channel.type == ChannelType.TELEGRAM
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("Agent already has a Telegram channel configured")
    
    # Validate Telegram bot token
    validation_result = await validate_telegram_bot_token(request.config.bot_token)
    
    # Create channel
    channel = Channel(
        agent_id=agent.id,
        type=ChannelType.TELEGRAM,
        status=ChannelStatus.CONFIGURING,
        config={
            "bot_token": request.config.bot_token,  # TODO: Encrypt in production
            "allowed_chat_ids": request.config.allowed_chat_ids,
            "bot_info": validation_result,
            "validated": True
        },
        configuration_steps=[]
    )
    
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    
    # Generate configuration steps
    config_steps = get_telegram_configuration_steps(str(channel.id))
    channel.configuration_steps = config_steps
    await db.commit()
    await db.refresh(channel)
    
    channel_data = ChannelResponse(
        id=str(channel.id),
        agent_id=str(channel.agent_id),
        type=channel.type.value,
        status=channel.status.value,
        config={k: v for k, v in channel.config.items() if k != 'bot_token'},  # Don't expose token
        configuration_steps=channel.configuration_steps,
        test_message_sent=channel.test_message_sent,
        last_test_at=channel.last_test_at.isoformat() if channel.last_test_at else None,
        created_at=channel.created_at.isoformat(),
        updated_at=channel.updated_at.isoformat()
    )
    
    return success_response(
        channel_data.dict(),
        "Telegram channel created successfully. Please follow the configuration steps."
    )


@router.get("")
async def list_channels(
    agent_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    pagination: tuple = Depends(get_pagination_params),
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List channels.
    
    Args:
        agent_id: Optional agent ID filter
        status_filter: Optional status filter
        type_filter: Optional type filter
        pagination: Pagination parameters
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of channels with pagination
    """
    skip, limit = pagination
    
    # Build query - join with Agent and VM to filter by user
    query = (
        select(Channel)
        .join(Agent)
        .join(Agent.vm)
    )
    
    # Filter by user through VM
    from app.infrastructure.database.models import VM
    query = query.where(VM.user_id == current_user.id)
    
    if agent_id:
        # Validate UUID format
        validate_uuid(agent_id, "Agent")
        # Verify agent ownership
        await verify_agent_ownership(agent_id, str(current_user.id), db)
        query = query.where(Channel.agent_id == agent_id)
    
    if status_filter:
        query = query.where(Channel.status == status_filter)
    
    if type_filter:
        query = query.where(Channel.type == type_filter)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(Channel.created_at.desc())
    result = await db.execute(query)
    channels = result.scalars().all()
    
    # Build response
    items = []
    for channel in channels:
        config = channel.config.copy()
        # Remove sensitive data
        config.pop('app_secret', None)
        config.pop('bot_token', None)
        
        items.append(
            ChannelResponse(
                id=str(channel.id),
                agent_id=str(channel.agent_id),
                type=channel.type.value,
                status=channel.status.value,
                config=config,
                configuration_steps=channel.configuration_steps,
                test_message_sent=channel.test_message_sent,
                last_test_at=channel.last_test_at.isoformat() if channel.last_test_at else None,
                created_at=channel.created_at.isoformat(),
                updated_at=channel.updated_at.isoformat()
            ).dict()
        )
    
    page = (skip // limit) + 1 if limit > 0 else 1
    return paginated_response(items, total, page, limit)


@router.get("/{channel_id}")
async def get_channel(
    channel_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get channel details.
    
    Args:
        channel_id: Channel ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Channel details
        
    Raises:
        NotFoundError: If channel not found
        ForbiddenError: If channel's agent doesn't belong to user
    """
    # Validate UUID format
    validate_uuid(channel_id, "Channel")
    
    try:
        result = await db.execute(select(Channel).where(Channel.id == channel_id))
        channel = result.scalar_one_or_none()
    except (StatementError, DataError) as e:
        raise NotFoundError("Channel", channel_id)
    
    if not channel:
        raise NotFoundError("Channel", channel_id)
    
    # Verify ownership through agent
    await verify_agent_ownership(str(channel.agent_id), str(current_user.id), db)
    
    config = channel.config.copy()
    # Remove sensitive data
    config.pop('app_secret', None)
    config.pop('bot_token', None)
    
    channel_data = ChannelResponse(
        id=str(channel.id),
        agent_id=str(channel.agent_id),
        type=channel.type.value,
        status=channel.status.value,
        config=config,
        configuration_steps=channel.configuration_steps,
        test_message_sent=channel.test_message_sent,
        last_test_at=channel.last_test_at.isoformat() if channel.last_test_at else None,
        created_at=channel.created_at.isoformat(),
        updated_at=channel.updated_at.isoformat()
    )
    
    return success_response(channel_data.dict())


@router.get("/{channel_id}/status")
async def get_channel_status(
    channel_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check channel connection status.
    
    Args:
        channel_id: Channel ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Channel status with connection details
        
    Raises:
        NotFoundError: If channel not found
        ForbiddenError: If channel's agent doesn't belong to user
    """
    # Validate UUID format
    validate_uuid(channel_id, "Channel")
    
    try:
        result = await db.execute(select(Channel).where(Channel.id == channel_id))
        channel = result.scalar_one_or_none()
    except (StatementError, DataError) as e:
        raise NotFoundError("Channel", channel_id)
    
    if not channel:
        raise NotFoundError("Channel", channel_id)
    
    # Verify ownership through agent
    await verify_agent_ownership(str(channel.agent_id), str(current_user.id), db)
    
    # Check connection status based on channel type
    is_connected = False
    details = {}
    
    if channel.type == ChannelType.FEISHU:
        # Validate Feishu credentials
        app_id = channel.config.get('app_id')
        app_secret = channel.config.get('app_secret')
        
        if app_id and app_secret:
            try:
                validation = await validate_feishu_credentials(app_id, app_secret)
                is_connected = validation.get('valid', False)
                details = {
                    "app_id": app_id,
                    "validated": is_connected
                }
            except Exception as e:
                details = {
                    "error": str(e),
                    "validated": False
                }
    
    elif channel.type == ChannelType.TELEGRAM:
        # Validate Telegram bot token
        bot_token = channel.config.get('bot_token')
        
        if bot_token:
            try:
                validation = await validate_telegram_bot_token(bot_token)
                is_connected = validation.get('valid', False)
                details = {
                    "bot_username": validation.get('bot_username'),
                    "bot_name": validation.get('bot_name'),
                    "validated": is_connected
                }
            except Exception as e:
                details = {
                    "error": str(e),
                    "validated": False
                }
    
    # Update channel status
    if is_connected:
        channel.status = ChannelStatus.ACTIVE
    else:
        channel.status = ChannelStatus.ERROR
    
    channel.updated_at = datetime.utcnow()
    await db.commit()
    
    status_data = ChannelStatusResponse(
        channel_id=str(channel.id),
        type=channel.type.value,
        status=channel.status.value,
        is_connected=is_connected,
        details=details
    )
    
    return success_response(status_data.dict())


@router.post("/{channel_id}/test")
async def send_test_message(
    channel_id: str,
    request: Optional[TestMessageRequest] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a test message through the channel.
    
    Args:
        channel_id: Channel ID
        request: Test message request (optional)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Test message result
        
    Raises:
        NotFoundError: If channel not found
        ForbiddenError: If channel's agent doesn't belong to user
        BadRequestError: If channel is not active or test fails
    """
    # Validate UUID format
    validate_uuid(channel_id, "Channel")
    
    try:
        result = await db.execute(select(Channel).where(Channel.id == channel_id))
        channel = result.scalar_one_or_none()
    except (StatementError, DataError) as e:
        raise NotFoundError("Channel", channel_id)
    
    if not channel:
        raise NotFoundError("Channel", channel_id)
    
    # Verify ownership through agent
    await verify_agent_ownership(str(channel.agent_id), str(current_user.id), db)
    
    # Check channel status
    if channel.status not in [ChannelStatus.ACTIVE, ChannelStatus.CONFIGURING]:
        raise BadRequestError("Channel is not ready for testing")
    
    message = request.message if request else "This is a test message from OpenClaw VM Platform"
    test_result = {
        "success": False,
        "message": message,
        "error": None
    }
    
    # Send test message based on channel type
    if channel.type == ChannelType.FEISHU:
        # TODO: Implement Feishu test message sending
        # For now, just validate credentials
        app_id = channel.config.get('app_id')
        app_secret = channel.config.get('app_secret')
        
        if app_id and app_secret:
            try:
                validation = await validate_feishu_credentials(app_id, app_secret)
                test_result["success"] = True
                test_result["message"] = "Feishu credentials validated successfully"
            except Exception as e:
                test_result["error"] = str(e)
    
    elif channel.type == ChannelType.TELEGRAM:
        # TODO: Implement Telegram test message sending
        # For now, just validate bot token
        bot_token = channel.config.get('bot_token')
        allowed_chat_ids = channel.config.get('allowed_chat_ids', [])
        
        if bot_token and allowed_chat_ids:
            try:
                validation = await validate_telegram_bot_token(bot_token)
                test_result["success"] = True
                test_result["message"] = f"Telegram bot validated. Bot: @{validation.get('bot_username')}"
            except Exception as e:
                test_result["error"] = str(e)
    
    # Update channel test status
    if test_result["success"]:
        channel.test_message_sent = True
        channel.last_test_at = datetime.utcnow()
        if channel.status == ChannelStatus.CONFIGURING:
            channel.status = ChannelStatus.ACTIVE
    
    channel.updated_at = datetime.utcnow()
    await db.commit()
    
    return success_response(
        test_result,
        "Test message sent successfully" if test_result["success"] else "Test message failed"
    )


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a channel.
    
    Args:
        channel_id: Channel ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Operation status
        
    Raises:
        NotFoundError: If channel not found
        ForbiddenError: If channel's agent doesn't belong to user
    """
    # Validate UUID format
    validate_uuid(channel_id, "Channel")
    
    try:
        result = await db.execute(select(Channel).where(Channel.id == channel_id))
        channel = result.scalar_one_or_none()
    except (StatementError, DataError) as e:
        raise NotFoundError("Channel", channel_id)
    
    if not channel:
        raise NotFoundError("Channel", channel_id)
    
    # Verify ownership through agent
    await verify_agent_ownership(str(channel.agent_id), str(current_user.id), db)
    
    # Delete channel
    try:
        await db.delete(channel)
        await db.commit()
    except (StatementError, DataError) as e:
        await db.rollback()
        raise NotFoundError("Channel", channel_id)
    
    return success_response(
        {
            "id": channel_id,
            "message": "Channel deleted successfully"
        },
        "Channel deletion completed"
    )
