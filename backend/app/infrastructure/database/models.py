"""
SQLAlchemy database models for the application.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Numeric, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.infrastructure.database.base import Base


class UserRole(str, enum.Enum):
    """User role enum."""
    USER = "user"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    """User status enum."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class VMStatus(str, enum.Enum):
    """VM status enum."""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DELETING = "deleting"


class AgentStatus(str, enum.Enum):
    """Agent status enum."""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class ChannelType(str, enum.Enum):
    """Channel type enum."""
    FEISHU = "feishu"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    WEBCHAT = "webchat"


class ChannelStatus(str, enum.Enum):
    """Channel status enum."""
    PENDING = "pending"
    CONFIGURING = "configuring"
    ACTIVE = "active"
    ERROR = "error"


class OrderType(str, enum.Enum):
    """Order type enum."""
    RECHARGE = "recharge"
    SUBSCRIPTION = "subscription"
    TOKEN_USAGE = "token_usage"
    DISK_EXPANSION = "disk_expansion"
    BACKUP = "backup"


class OrderStatus(str, enum.Enum):
    """Order status enum."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    balance = Column(Numeric(10, 2), default=0.00)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vms = relationship("VM", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")


class Plan(Base):
    """Plan (套餐) model."""
    __tablename__ = "plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    cpu = Column(Integer, nullable=False)
    memory = Column(Integer, nullable=False)  # MB
    disk = Column(Integer, nullable=False)    # GB
    max_agents = Column(Integer, nullable=False)
    max_channels = Column(Integer, nullable=False)
    price_per_month = Column(Numeric(10, 2), nullable=False)
    features = Column(JSONB, default=list)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vms = relationship("VM", back_populates="plan")


class VM(Base):
    """Virtual Machine model."""
    __tablename__ = "vms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    name = Column(String(100), nullable=False)
    status = Column(SQLEnum(VMStatus), default=VMStatus.CREATING, index=True)
    
    # VM Configuration
    libvirt_domain_name = Column(String(255), unique=True)
    ip_address = Column(INET)
    mac_address = Column(String(17))
    
    # Resource Configuration
    cpu = Column(Integer, nullable=False)
    memory = Column(Integer, nullable=False)
    disk = Column(Integer, nullable=False)
    
    # Time Information
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_start_at = Column(DateTime(timezone=True))
    last_stop_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="vms")
    plan = relationship("Plan", back_populates="vms")
    agents = relationship("Agent", back_populates="vm", cascade="all, delete-orphan")
    token_usages = relationship("TokenUsage", back_populates="vm", cascade="all, delete-orphan")


class AgentTemplate(Base):
    """Agent template model."""
    __tablename__ = "agent_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    category = Column(String(50), nullable=False, index=True)
    system_prompt = Column(Text, nullable=False)
    default_config = Column(JSONB, default=dict)
    features = Column(JSONB, default=list)
    preview_image = Column(String(255))
    is_popular = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agents = relationship("Agent", back_populates="template")


class Agent(Base):
    """Agent model."""
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vm_id = Column(UUID(as_uuid=True), ForeignKey("vms.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("agent_templates.id"))
    name = Column(String(100), nullable=False)
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.CREATING, index=True)
    
    # Configuration
    system_prompt = Column(Text)
    model_config = Column(JSONB, nullable=False)
    
    # Statistics
    messages_count = Column(Integer, default=0)
    last_active_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vm = relationship("VM", back_populates="agents")
    template = relationship("AgentTemplate", back_populates="agents")
    channels = relationship("Channel", back_populates="agent", cascade="all, delete-orphan")
    token_usages = relationship("TokenUsage", back_populates="agent", cascade="all, delete-orphan")


class Channel(Base):
    """Channel model."""
    __tablename__ = "channels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(SQLEnum(ChannelType), nullable=False, index=True)
    status = Column(SQLEnum(ChannelStatus), default=ChannelStatus.PENDING, index=True)
    
    # Configuration
    config = Column(JSONB, nullable=False)
    
    # Configuration Steps
    configuration_steps = Column(JSONB, default=list)
    
    # Test
    test_message_sent = Column(Boolean, default=False)
    last_test_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="channels")


class TokenUsage(Base):
    """Token usage record model."""
    __tablename__ = "token_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    vm_id = Column(UUID(as_uuid=True), ForeignKey("vms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    cost = Column(Numeric(10, 6), nullable=False)
    
    # Request Information
    request_id = Column(String(255))
    extra_data = Column(JSONB, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="token_usages")
    vm = relationship("VM", back_populates="token_usages")


class Order(Base):
    """Order model."""
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    vm_id = Column(UUID(as_uuid=True), ForeignKey("vms.id"), index=True)
    
    type = Column(SQLEnum(OrderType), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    balance_before = Column(Numeric(10, 2), nullable=False)
    balance_after = Column(Numeric(10, 2), nullable=False)
    
    description = Column(Text)
    extra_data = Column(JSONB, default=dict)
    
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.COMPLETED)
    
    # Payment Information
    payment_method = Column(String(20))
    payment_transaction_id = Column(String(255))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", back_populates="orders")


class Model(Base):
    """Model configuration model."""
    __tablename__ = "models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)
    api_endpoint = Column(String(255), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    
    # Pricing
    price_per_1k_tokens = Column(Numeric(10, 4), nullable=False)
    
    # Configuration
    max_tokens = Column(Integer)
    default_config = Column(JSONB, default=dict)
    
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SystemConfig(Base):
    """System configuration model."""
    __tablename__ = "system_configs"
    
    key = Column(String(100), primary_key=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
