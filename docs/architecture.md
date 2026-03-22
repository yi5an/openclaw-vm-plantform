# OpenClaw VM Platform - 技术架构设计 v3.0

> **架构师**: Architect  
> **技术栈**: React + Python/FastAPI + PostgreSQL + Redis + KVM/Libvirt  
> **最后更新**: 2026-03-21  
> **状态**: ✅ 已完成

---

## 📋 目录

1. [系统架构概览](#1-系统架构概览)
2. [分层架构设计](#2-分层架构设计)
3. [核心组件设计](#3-核心组件设计)
4. [API 接口规范](#4-api-接口规范)
5. [数据库模型设计](#5-数据库模型设计)
6. [缓存策略设计](#6-缓存策略设计)
7. [KVM/Libvirt 集成方案](#7-kvmlibvirt-集成方案)
8. [安全架构设计](#8-安全架构设计)
9. [部署架构](#9-部署架构)
10. [技术选型说明](#10-技术选型说明)

---

## 1. 系统架构概览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户层 (User Layer)                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │        Web Portal (React + TypeScript + Vite)         │  │
│  │  注册登录 │ 实例管理 │ Agent配置 │ 渠道配置 │ 监控     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTPS/WSS
┌─────────────────────────────────────────────────────────────┐
│                    网关层 (Gateway Layer)                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │        Nginx Reverse Proxy (负载均衡 + SSL 终结)       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   应用层 (Application Layer)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           FastAPI Application (Port 8000)            │   │
│  │  ┌─────────┬─────────┬─────────┬─────────┬────────┐ │   │
│  │  │User API │ VM API  │Agent API│Channel  │Billing │ │   │
│  │  │         │         │         │  API    │  API   │ │   │
│  │  └─────────┴─────────┴─────────┴─────────┴────────┘ │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │        Middleware Stack                         │ │   │
│  │  │  Auth │ Rate Limit │ Logging │ CORS │ Error    │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   业务层 (Business Layer)                    │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │  User    │   VM     │  Agent   │ Channel  │ Billing  │  │
│  │ Service  │ Service  │ Service  │ Service  │ Service  │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 基础设施层 (Infrastructure Layer)             │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │PostgreSQL│  Redis   │ Libvirt  │   SSH    │  Email   │  │
│  │  (数据)  │ (缓存)   │  (VM)    │ (远程)   │ (通知)   │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  宿主机层 (Host Machine Layer)               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              KVM Hypervisor (Linux Host)              │  │
│  │  ┌──────────┬──────────┬──────────┬──────────┐       │  │
│  │  │  VM #1   │  VM #2   │  VM #3   │  VM #N   │       │  │
│  │  │OpenClaw  │OpenClaw  │OpenClaw  │OpenClaw  │       │  │
│  │  │ Instance │ Instance │ Instance │ Instance │       │  │
│  │  └──────────┴──────────┴──────────┴──────────┘       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 数据流图

```
用户请求
   ↓
[Nginx] → SSL 终结、负载均衡
   ↓
[FastAPI] → 认证、限流、路由
   ↓
[Business Service] → 业务逻辑处理
   ↓
┌─────────┬─────────┬─────────┐
│PostgreSQL│  Redis  │ Libvirt │
└─────────┴─────────┴─────────┘
   ↓           ↓         ↓
 持久化      缓存      VM操作
```

---

## 2. 分层架构设计

### 2.1 六边形架构（Hexagonal Architecture）

采用六边形架构（端口与适配器模式），确保业务逻辑与技术实现解耦。

```
                    ┌─────────────────┐
                    │   Web Adapter   │ (FastAPI Routes)
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
    │  Auth   │        │   API   │        │  Event  │
    │ Adapter │        │ Adapter │        │ Adapter │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Application    │
                    │    Core         │
                    │  ┌───────────┐  │
                    │  │  Domain   │  │
                    │  │  Models   │  │
                    │  └───────────┘  │
                    │  ┌───────────┐  │
                    │  │ Services  │  │
                    │  └───────────┘  │
                    │  ┌───────────┐  │
                    │  │  Ports    │  │
                    │  └───────────┘  │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
    │   DB    │        │  Cache  │        │   VM    │
    │ Adapter │        │ Adapter │        │ Adapter │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                   │                   │
    ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
    │PostgreSQL│       │  Redis  │        │ Libvirt │
    └─────────┘        └─────────┘        └─────────┘
```

### 2.2 目录结构

```
openclaw-vm-platform/
├── frontend/                    # 前端应用
│   ├── src/
│   │   ├── components/         # React 组件
│   │   ├── pages/              # 页面
│   │   ├── hooks/              # 自定义 Hooks
│   │   ├── services/           # API 调用
│   │   └── utils/              # 工具函数
│   └── package.json
│
├── backend/                     # 后端应用
│   ├── app/
│   │   ├── api/                # API 层（适配器）
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── vms.py
│   │   │   │   ├── agents.py
│   │   │   │   ├── channels.py
│   │   │   │   └── billing.py
│   │   │   └── deps.py         # 依赖注入
│   │   │
│   │   ├── core/               # 应用核心
│   │   │   ├── config.py       # 配置管理
│   │   │   ├── security.py     # 安全工具
│   │   │   └── exceptions.py   # 异常定义
│   │   │
│   │   ├── domain/             # 领域模型
│   │   │   ├── entities/       # 实体
│   │   │   │   ├── user.py
│   │   │   │   ├── vm.py
│   │   │   │   ├── agent.py
│   │   │   │   └── channel.py
│   │   │   └── value_objects/  # 值对象
│   │   │
│   │   ├── services/           # 业务服务
│   │   │   ├── user_service.py
│   │   │   ├── vm_service.py
│   │   │   ├── agent_service.py
│   │   │   └── billing_service.py
│   │   │
│   │   ├── repositories/       # 仓储接口（端口）
│   │   │   ├── user_repo.py
│   │   │   ├── vm_repo.py
│   │   │   └── agent_repo.py
│   │   │
│   │   ├── infrastructure/     # 基础设施（适配器）
│   │   │   ├── database/
│   │   │   │   ├── models.py   # SQLAlchemy Models
│   │   │   │   └── repositories.py
│   │   │   ├── cache/
│   │   │   │   └── redis_client.py
│   │   │   ├── vm/
│   │   │   │   ├── libvirt_manager.py
│   │   │   │   └── ssh_client.py
│   │   │   └── messaging/
│   │   │       └── email_sender.py
│   │   │
│   │   └── main.py             # FastAPI 应用入口
│   │
│   ├── tests/                  # 测试
│   ├── alembic/                # 数据库迁移
│   ├── requirements.txt
│   └── pyproject.toml
│
├── docs/                        # 文档
├── scripts/                     # 部署脚本
└── docker-compose.yml          # 容器编排
```

---

## 3. 核心组件设计

### 3.1 FastAPI 应用配置

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.api.v1 import auth, users, vms, agents, channels, billing
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers

app = FastAPI(
    title="OpenClaw VM Platform API",
    version="1.0.0",
    description="虚拟机租赁平台 API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 异常处理
setup_exception_handlers(app)

# 路由注册
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])
app.include_router(vms.router, prefix="/api/v1/vms", tags=["虚拟机"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agent"])
app.include_router(channels.router, prefix="/api/v1/channels", tags=["渠道"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["计费"])


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    # 初始化数据库连接池
    # 初始化 Redis 连接池
    # 初始化 Libvirt 连接
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    # 清理资源
    pass
```

### 3.2 配置管理

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "OpenClaw VM Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API 配置
    API_V1_PREFIX: str = "/api/v1"
    
    # 数据库配置
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    
    # Redis 配置
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 50
    
    # JWT 配置
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Libvirt 配置
    LIBVIRT_URI: str = "qemu:///system"
    LIBVIRT_POOL_NAME: str = "openclaw-vms"
    LIBVIRT_NETWORK_NAME: str = "openclaw-network"
    
    # SSH 配置
    SSH_PRIVATE_KEY_PATH: str = "/root/.ssh/id_rsa"
    SSH_USER: str = "root"
    
    # 虚拟机配置
    VM_BASE_IMAGE_PATH: str = "/var/lib/libvirt/images/base.qcow2"
    VM_DEFAULT_CPU: int = 1
    VM_DEFAULT_MEMORY: int = 2048  # MB
    VM_DEFAULT_DISK: int = 20      # GB
    
    # 计费配置
    TOKEN_PRICE_PER_1K: float = 0.01
    DISK_PRICE_PER_GB: float = 0.5
    BACKUP_PRICE_PER_MONTH: float = 20.0
    
    # CORS 配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # 限流配置
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
```

---

## 4. API 接口规范

### 4.1 认证模块 (`/api/v1/auth`)

#### 用户注册
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "username": "johndoe"
}

Response 201:
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "created_at": "2026-03-21T10:00:00Z"
}
```

#### 用户登录
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=SecurePass123!

Response 200:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### 刷新 Token
```http
POST /api/v1/auth/refresh
Authorization: Bearer {refresh_token}

Response 200:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 4.2 用户模块 (`/api/v1/users`)

#### 获取当前用户信息
```http
GET /api/v1/users/me
Authorization: Bearer {access_token}

Response 200:
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "johndoe",
  "balance": 100.50,
  "created_at": "2026-03-21T10:00:00Z",
  "updated_at": "2026-03-21T12:00:00Z"
}
```

#### 更新用户信息
```http
PATCH /api/v1/users/me
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "username": "newname"
}

Response 200:
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "newname",
  "updated_at": "2026-03-21T13:00:00Z"
}
```

#### 充值余额
```http
POST /api/v1/users/me/recharge
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "amount": 100.00,
  "payment_method": "alipay"
}

Response 200:
{
  "order_id": "uuid",
  "amount": 100.00,
  "payment_url": "https://payment.example.com/pay/xxx",
  "status": "pending"
}
```

### 4.3 虚拟机模块 (`/api/v1/vms`)

#### 创建虚拟机
```http
POST /api/v1/vms
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "my-openclaw-instance",
  "plan_id": "uuid",
  "agent_template_id": "uuid",
  "region": "cn-east-1"
}

Response 201:
{
  "id": "uuid",
  "name": "my-openclaw-instance",
  "status": "creating",
  "plan": {
    "id": "uuid",
    "name": "标准版",
    "cpu": 2,
    "memory": 4096,
    "disk": 40
  },
  "created_at": "2026-03-21T10:00:00Z",
  "estimated_ready_at": "2026-03-21T10:05:00Z"
}
```

#### 获取虚拟机列表
```http
GET /api/v1/vms?page=1&page_size=20&status=running
Authorization: Bearer {access_token}

Response 200:
{
  "items": [
    {
      "id": "uuid",
      "name": "my-openclaw-instance",
      "status": "running",
      "ip_address": "192.168.1.100",
      "plan": {
        "id": "uuid",
        "name": "标准版",
        "cpu": 2,
        "memory": 4096,
        "disk": 40
      },
      "agents_count": 2,
      "expires_at": "2026-04-21T10:00:00Z",
      "created_at": "2026-03-21T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "pages": 1
}
```

#### 获取虚拟机详情
```http
GET /api/v1/vms/{vm_id}
Authorization: Bearer {access_token}

Response 200:
{
  "id": "uuid",
  "name": "my-openclaw-instance",
  "status": "running",
  "ip_address": "192.168.1.100",
  "plan": {
    "id": "uuid",
    "name": "标准版",
    "cpu": 2,
    "memory": 4096,
    "disk": 40,
    "price_per_month": 199.00
  },
  "agents": [
    {
      "id": "uuid",
      "name": "客服助手",
      "status": "running",
      "model": "gpt-4"
    }
  ],
  "channels": [
    {
      "id": "uuid",
      "type": "feishu",
      "status": "active"
    }
  ],
  "usage": {
    "cpu_percent": 15.5,
    "memory_percent": 45.2,
    "disk_percent": 30.0,
    "network_in_bytes": 1073741824,
    "network_out_bytes": 536870912
  },
  "billing": {
    "current_month_cost": 50.25,
    "token_usage": 150000,
    "token_cost": 1.50
  },
  "expires_at": "2026-04-21T10:00:00Z",
  "created_at": "2026-03-21T10:00:00Z",
  "updated_at": "2026-03-21T12:00:00Z"
}
```

#### 启动虚拟机
```http
POST /api/v1/vms/{vm_id}/start
Authorization: Bearer {access_token}

Response 200:
{
  "id": "uuid",
  "status": "starting",
  "message": "虚拟机正在启动"
}
```

#### 停止虚拟机
```http
POST /api/v1/vms/{vm_id}/stop
Authorization: Bearer {access_token}

Response 200:
{
  "id": "uuid",
  "status": "stopping",
  "message": "虚拟机正在停止"
}
```

#### 删除虚拟机
```http
DELETE /api/v1/vms/{vm_id}
Authorization: Bearer {access_token}

Response 200:
{
  "id": "uuid",
  "status": "deleting",
  "message": "虚拟机正在删除，所有数据将被清除"
}
```

#### 续费虚拟机
```http
POST /api/v1/vms/{vm_id}/renew
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "months": 1
}

Response 200:
{
  "id": "uuid",
  "expires_at": "2026-05-21T10:00:00Z",
  "cost": 199.00,
  "new_balance": 0.50
}
```

### 4.4 Agent 模块 (`/api/v1/agents`)

#### 获取 Agent 模板列表
```http
GET /api/v1/agents/templates
Authorization: Bearer {access_token}

Response 200:
{
  "items": [
    {
      "id": "uuid",
      "name": "客服助手",
      "description": "智能客服机器人，支持多轮对话",
      "category": "customer_service",
      "features": ["多轮对话", "情感分析", "工单创建"],
      "preview_image": "https://example.com/template.jpg",
      "is_popular": true
    }
  ],
  "total": 8
}
```

#### 创建 Agent
```http
POST /api/v1/agents
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "vm_id": "uuid",
  "name": "我的客服助手",
  "template_id": "uuid",
  "model_config": {
    "provider": "platform",
    "model_id": "uuid"
  }
}

或自定义创建：
{
  "vm_id": "uuid",
  "name": "自定义 Agent",
  "custom_config": {
    "system_prompt": "你是一个专业的客服...",
    "model_config": {
      "provider": "custom",
      "api_key": "sk-xxx",
      "model_name": "gpt-4"
    }
  }
}

Response 201:
{
  "id": "uuid",
  "name": "我的客服助手",
  "status": "creating",
  "template": {
    "id": "uuid",
    "name": "客服助手"
  },
  "model": {
    "provider": "platform",
    "model_name": "gpt-4"
  },
  "created_at": "2026-03-21T10:00:00Z"
}
```

#### 获取 VM 下的 Agent 列表
```http
GET /api/v1/agents?vm_id={vm_id}
Authorization: Bearer {access_token}

Response 200:
{
  "items": [
    {
      "id": "uuid",
      "name": "我的客服助手",
      "status": "running",
      "template_name": "客服助手",
      "model": "gpt-4",
      "channels_count": 2,
      "messages_count": 1500,
      "created_at": "2026-03-21T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### 更新 Agent 配置
```http
PATCH /api/v1/agents/{agent_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "system_prompt": "你是一个更加友好的客服...",
  "model_config": {
    "temperature": 0.7
  }
}

Response 200:
{
  "id": "uuid",
  "name": "我的客服助手",
  "system_prompt": "你是一个更加友好的客服...",
  "updated_at": "2026-03-21T13:00:00Z"
}
```

#### 启动/停止 Agent
```http
POST /api/v1/agents/{agent_id}/start
POST /api/v1/agents/{agent_id}/stop
Authorization: Bearer {access_token}

Response 200:
{
  "id": "uuid",
  "status": "running"
}
```

#### 删除 Agent
```http
DELETE /api/v1/agents/{agent_id}
Authorization: Bearer {access_token}

Response 204 No Content
```

#### 验证自定义 Token
```http
POST /api/v1/agents/validate-token
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "provider": "openai",
  "api_key": "sk-xxx",
  "model_name": "gpt-4"
}

Response 200:
{
  "valid": true,
  "model_info": {
    "name": "gpt-4",
    "max_tokens": 8192
  }
}
```

### 4.5 渠道模块 (`/api/v1/channels`)

#### 配置飞书渠道
```http
POST /api/v1/channels/feishu
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "agent_id": "uuid",
  "app_id": "cli_xxx",
  "app_secret": "xxx"
}

Response 201:
{
  "id": "uuid",
  "type": "feishu",
  "agent_id": "uuid",
  "status": "configuring",
  "steps": [
    {
      "step": "validate_credentials",
      "status": "completed"
    },
    {
      "step": "configure_webhook",
      "status": "in_progress"
    },
    {
      "step": "set_permissions",
      "status": "pending"
    }
  ],
  "next_action": {
    "type": "visit_url",
    "url": "https://open.feishu.cn/app/xxx",
    "instruction": "请在飞书开放平台配置事件订阅地址：https://api.example.com/webhook/feishu/{channel_id}"
  }
}
```

#### 获取渠道配置状态
```http
GET /api/v1/channels/{channel_id}/status
Authorization: Bearer {access_token}

Response 200:
{
  "id": "uuid",
  "type": "feishu",
  "status": "active",
  "configuration_steps": [
    {
      "step": "validate_credentials",
      "status": "completed",
      "completed_at": "2026-03-21T10:00:00Z"
    },
    {
      "step": "configure_webhook",
      "status": "completed",
      "completed_at": "2026-03-21T10:05:00Z"
    },
    {
      "step": "set_permissions",
      "status": "completed",
      "completed_at": "2026-03-21T10:10:00Z"
    }
  ],
  "test_message_sent": true,
  "active_since": "2026-03-21T10:15:00Z"
}
```

#### 发送测试消息
```http
POST /api/v1/channels/{channel_id}/test
Authorization: Bearer {access_token}

Response 200:
{
  "success": true,
  "message": "测试消息已发送",
  "sent_at": "2026-03-21T10:20:00Z"
}
```

### 4.6 计费模块 (`/api/v1/billing`)

#### 获取套餐列表
```http
GET /api/v1/billing/plans

Response 200:
{
  "items": [
    {
      "id": "uuid",
      "name": "入门版",
      "cpu": 1,
      "memory": 2048,
      "disk": 20,
      "max_agents": 1,
      "max_channels": 2,
      "price_per_month": 99.00,
      "features": ["基础监控", "每日备份"]
    },
    {
      "id": "uuid",
      "name": "标准版",
      "cpu": 2,
      "memory": 4096,
      "disk": 40,
      "max_agents": 3,
      "max_channels": 5,
      "price_per_month": 199.00,
      "features": ["高级监控", "实时备份", "优先支持"]
    }
  ]
}
```

#### 获取消费记录
```http
GET /api/v1/billing/transactions?page=1&page_size=20
Authorization: Bearer {access_token}

Response 200:
{
  "items": [
    {
      "id": "uuid",
      "type": "recharge",
      "amount": 100.00,
      "balance_after": 100.00,
      "description": "账户充值",
      "created_at": "2026-03-21T10:00:00Z"
    },
    {
      "id": "uuid",
      "type": "deduction",
      "amount": -1.50,
      "balance_after": 98.50,
      "description": "Token 使用费用",
      "metadata": {
        "tokens": 150000,
        "model": "gpt-4"
      },
      "created_at": "2026-03-21T11:00:00Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20
}
```

#### 获取 Token 使用统计
```http
GET /api/v1/billing/token-usage?vm_id={vm_id}&period=month
Authorization: Bearer {access_token}

Response 200:
{
  "vm_id": "uuid",
  "period": "2026-03",
  "total_tokens": 150000,
  "total_cost": 1.50,
  "daily_usage": [
    {
      "date": "2026-03-21",
      "tokens": 5000,
      "cost": 0.05
    }
  ],
  "by_model": [
    {
      "model": "gpt-4",
      "tokens": 100000,
      "cost": 1.00
    },
    {
      "model": "gpt-3.5-turbo",
      "tokens": 50000,
      "cost": 0.50
    }
  ]
}
```

### 4.7 监控模块 (`/api/v1/monitoring`)

#### 获取实例监控数据
```http
GET /api/v1/monitoring/vms/{vm_id}/metrics?range=1h
Authorization: Bearer {access_token}

Response 200:
{
  "vm_id": "uuid",
  "range": "1h",
  "metrics": {
    "cpu": [
      {"timestamp": "2026-03-21T10:00:00Z", "value": 15.5},
      {"timestamp": "2026-03-21T10:05:00Z", "value": 18.2}
    ],
    "memory": [
      {"timestamp": "2026-03-21T10:00:00Z", "value": 45.2},
      {"timestamp": "2026-03-21T10:05:00Z", "value": 46.1}
    ],
    "network_in": [
      {"timestamp": "2026-03-21T10:00:00Z", "value": 1024},
      {"timestamp": "2026-03-21T10:05:00Z", "value": 2048}
    ],
    "network_out": [
      {"timestamp": "2026-03-21T10:00:00Z", "value": 512},
      {"timestamp": "2026-03-21T10:05:00Z", "value": 1024}
    ]
  }
}
```

### 4.8 管理员模块 (`/api/v1/admin`)

#### 用户管理
```http
GET /api/v1/admin/users?page=1&page_size=20
Authorization: Bearer {admin_token}

Response 200:
{
  "items": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "username": "johndoe",
      "balance": 100.50,
      "vms_count": 2,
      "status": "active",
      "created_at": "2026-03-21T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### 调整用户余额
```http
POST /api/v1/admin/users/{user_id}/adjust-balance
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "amount": 50.00,
  "reason": "补偿"
}

Response 200:
{
  "user_id": "uuid",
  "old_balance": 100.50,
  "new_balance": 150.50,
  "adjustment": 50.00
}
```

#### Agent 模板管理
```http
POST /api/v1/admin/agent-templates
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "客服助手",
  "description": "智能客服机器人",
  "category": "customer_service",
  "system_prompt": "你是一个专业的客服...",
  "default_config": {
    "temperature": 0.7,
    "max_tokens": 2000
  }
}

Response 201:
{
  "id": "uuid",
  "name": "客服助手",
  "created_at": "2026-03-21T10:00:00Z"
}
```

#### 模型管理
```http
POST /api/v1/admin/models
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "GPT-4",
  "provider": "openai",
  "api_endpoint": "https://api.openai.com/v1",
  "api_key": "sk-xxx",
  "price_per_1k_tokens": 0.01,
  "is_active": true
}

Response 201:
{
  "id": "uuid",
  "name": "GPT-4",
  "status": "active"
}
```

---

## 5. 数据库模型设计

### 5.1 ER 图

```
┌─────────────┐         ┌─────────────┐
│   users     │         │    plans    │
├─────────────┤         ├─────────────┤
│ id (PK)     │         │ id (PK)     │
│ email       │         │ name        │
│ username    │         │ cpu         │
│ password    │         │ memory      │
│ balance     │         │ disk        │
│ role        │         │ price       │
└──────┬──────┘         └──────┬──────┘
       │                       │
       │ 1:N                   │ 1:N
       │                       │
       ▼                       ▼
┌─────────────┐         ┌─────────────┐
│     vms     │◄────────│   orders    │
├─────────────┤  N:1    ├─────────────┤
│ id (PK)     │         │ id (PK)     │
│ user_id(FK) │         │ user_id(FK) │
│ plan_id(FK) │         │ vm_id (FK)  │
│ name        │         │ type        │
│ status      │         │ amount      │
│ ip_address  │         │ status      │
│ cpu         │         └─────────────┘
│ memory      │
│ disk        │         ┌─────────────┐
│ expires_at  │         │agent_templates│
└──────┬──────┘         ├─────────────┤
       │                │ id (PK)     │
       │ 1:N            │ name        │
       │                │ description │
       ▼                │ category    │
┌─────────────┐         └──────┬──────┘
│   agents    │◄───────────────┘
├─────────────┤    N:1
│ id (PK)     │
│ vm_id (FK)  │         ┌─────────────┐
│template_id(FK)│       │  channels   │
│ name        │         ├─────────────┤
│ status      │         │ id (PK)     │
│ model_config│◄────────│ agent_id(FK)│
└──────┬──────┘  1:N    │ type        │
       │                │ config      │
       │                │ status      │
       │                └─────────────┘
       │
       │ 1:N
       ▼
┌─────────────┐
│token_usage  │
├─────────────┤
│ id (PK)     │
│ agent_id(FK)│
│ model       │
│ tokens      │
│ cost        │
│ created_at  │
└─────────────┘
```

### 5.2 详细表结构

#### 用户表 (users)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    balance DECIMAL(10, 2) DEFAULT 0.00,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_users_email (email),
    INDEX idx_users_username (username),
    INDEX idx_users_status (status)
);
```

#### 套餐表 (plans)
```sql
CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    cpu INTEGER NOT NULL,
    memory INTEGER NOT NULL,  -- MB
    disk INTEGER NOT NULL,     -- GB
    max_agents INTEGER NOT NULL,
    max_channels INTEGER NOT NULL,
    price_per_month DECIMAL(10, 2) NOT NULL,
    features JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_plans_active (is_active, sort_order)
);
```

#### 虚拟机表 (vms)
```sql
CREATE TABLE vms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES plans(id),
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'creating' CHECK (status IN ('creating', 'running', 'stopped', 'error', 'deleting')),
    
    -- VM 配置
    libvirt_domain_name VARCHAR(255) UNIQUE,
    ip_address INET,
    mac_address VARCHAR(17),
    
    -- 资源配置
    cpu INTEGER NOT NULL,
    memory INTEGER NOT NULL,
    disk INTEGER NOT NULL,
    
    -- 时间信息
    expires_at TIMESTAMP NOT NULL,
    last_start_at TIMESTAMP,
    last_stop_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    CONSTRAINT chk_vm_name UNIQUE (user_id, name),
    
    INDEX idx_vms_user (user_id),
    INDEX idx_vms_status (status),
    INDEX idx_vms_expires (expires_at)
);
```

#### Agent 模板表 (agent_templates)
```sql
CREATE TABLE agent_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    system_prompt TEXT NOT NULL,
    default_config JSONB DEFAULT '{}',
    features JSONB DEFAULT '[]',
    preview_image VARCHAR(255),
    is_popular BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_templates_category (category),
    INDEX idx_templates_active (is_active, is_popular)
);
```

#### Agent 表 (agents)
```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vm_id UUID NOT NULL REFERENCES vms(id) ON DELETE CASCADE,
    template_id UUID REFERENCES agent_templates(id),
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'creating' CHECK (status IN ('creating', 'running', 'stopped', 'error')),
    
    -- 配置
    system_prompt TEXT,
    model_config JSONB NOT NULL,  -- {"provider": "platform"|"custom", "model_id": "uuid"|"model_name": "gpt-4", "api_key": "xxx"}
    
    -- 统计
    messages_count INTEGER DEFAULT 0,
    last_active_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_agents_vm (vm_id),
    INDEX idx_agents_status (status)
);
```

#### 渠道表 (channels)
```sql
CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL CHECK (type IN ('feishu', 'telegram', 'whatsapp', 'webchat')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'configuring', 'active', 'error')),
    
    -- 配置
    config JSONB NOT NULL,  -- 加密存储敏感信息
    
    -- 配置步骤
    configuration_steps JSONB DEFAULT '[]',
    
    -- 测试
    test_message_sent BOOLEAN DEFAULT false,
    last_test_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_channels_agent (agent_id),
    INDEX idx_channels_type (type),
    INDEX idx_channels_status (status)
);
```

#### Token 使用记录表 (token_usage)
```sql
CREATE TABLE token_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    vm_id UUID NOT NULL REFERENCES vms(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    model VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost DECIMAL(10, 6) NOT NULL,
    
    -- 请求信息
    request_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 分区键（按月分区）
    CONSTRAINT token_usage_created_at_check CHECK (created_at IS NOT NULL),
    
    INDEX idx_token_usage_agent (agent_id, created_at DESC),
    INDEX idx_token_usage_vm (vm_id, created_at DESC),
    INDEX idx_token_usage_user (user_id, created_at DESC)
);

-- 创建按月分区
CREATE TABLE token_usage_2026_03 PARTITION OF token_usage
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
```

#### 订单表 (orders)
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    vm_id UUID REFERENCES vms(id),
    
    type VARCHAR(20) NOT NULL CHECK (type IN ('recharge', 'subscription', 'token_usage', 'disk_expansion', 'backup')),
    amount DECIMAL(10, 2) NOT NULL,
    balance_before DECIMAL(10, 2) NOT NULL,
    balance_after DECIMAL(10, 2) NOT NULL,
    
    description TEXT,
    metadata JSONB DEFAULT '{}',
    
    status VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    
    -- 支付信息
    payment_method VARCHAR(20),
    payment_transaction_id VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_orders_user (user_id, created_at DESC),
    INDEX idx_orders_vm (vm_id),
    INDEX idx_orders_type (type, created_at DESC)
);
```

#### 模型配置表 (models)
```sql
CREATE TABLE models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    api_endpoint VARCHAR(255) NOT NULL,
    api_key_encrypted TEXT NOT NULL,  -- 加密存储
    
    -- 定价
    price_per_1k_tokens DECIMAL(10, 4) NOT NULL,
    
    -- 配置
    max_tokens INTEGER,
    default_config JSONB DEFAULT '{}',
    
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_models_active (is_active)
);
```

#### 系统配置表 (system_configs)
```sql
CREATE TABLE system_configs (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES users(id)
);
```

### 5.3 视图定义

#### 月度统计视图
```sql
CREATE VIEW monthly_statistics AS
SELECT 
    u.id AS user_id,
    u.email,
    DATE_TRUNC('month', tu.created_at) AS month,
    COUNT(DISTINCT v.id) AS active_vms,
    COUNT(DISTINCT a.id) AS active_agents,
    SUM(tu.total_tokens) AS total_tokens,
    SUM(tu.cost) AS total_cost
FROM users u
LEFT JOIN vms v ON v.user_id = u.id
LEFT JOIN agents a ON a.vm_id = v.id
LEFT JOIN token_usage tu ON tu.agent_id = a.id
GROUP BY u.id, u.email, DATE_TRUNC('month', tu.created_at);
```

#### 实例概览视图
```sql
CREATE VIEW vm_overview AS
SELECT 
    v.id,
    v.user_id,
    v.name,
    v.status,
    v.ip_address,
    v.expires_at,
    p.name AS plan_name,
    COUNT(DISTINCT a.id) AS agents_count,
    COUNT(DISTINCT c.id) AS channels_count,
    COALESCE(SUM(tu.total_tokens), 0) AS total_tokens,
    COALESCE(SUM(tu.cost), 0) AS total_cost
FROM vms v
JOIN plans p ON p.id = v.plan_id
LEFT JOIN agents a ON a.vm_id = v.id
LEFT JOIN channels c ON c.agent_id = a.id
LEFT JOIN token_usage tu ON tu.vm_id = v.id
GROUP BY v.id, v.user_id, v.name, v.status, v.ip_address, v.expires_at, p.name;
```

---

## 6. 缓存策略设计

### 6.1 Redis 数据结构设计

```
# 用户会话
session:{session_id}
  - type: hash
  - ttl: 1800s (30 min)
  - fields: user_id, email, role, created_at

# 用户信息缓存
user:{user_id}
  - type: hash
  - ttl: 3600s (1 hour)
  - fields: email, username, balance, role, status

# VM 状态缓存
vm:{vm_id}:status
  - type: hash
  - ttl: 60s
  - fields: status, cpu_percent, memory_percent, updated_at

# VM 列表缓存
user:{user_id}:vms
  - type: list
  - ttl: 300s (5 min)
  - value: [vm_id1, vm_id2, ...]

# Token 使用量实时统计
usage:{vm_id}:{month}
  - type: hash
  - ttl: 2592000s (30 days)
  - fields: total_tokens, total_cost, updated_at

# 限流计数器
ratelimit:{ip}:{endpoint}
  - type: string (counter)
  - ttl: 60s
  - value: request_count

# 分布式锁
lock:vm:{vm_id}:operation
  - type: string
  - ttl: 30s
  - value: operation_id

# Agent 状态缓存
agent:{agent_id}:status
  - type: hash
  - ttl: 30s
  - fields: status, messages_count, last_active_at

# 模型价格缓存
model:{model_id}:price
  - type: string
  - ttl: 86400s (24 hours)
  - value: price_per_1k_tokens
```

### 6.2 缓存策略

#### Cache-Aside Pattern
```python
async def get_user(user_id: str) -> User:
    # 1. 尝试从缓存获取
    cache_key = f"user:{user_id}"
    cached = await redis.hgetall(cache_key)
    
    if cached:
        return User(**cached)
    
    # 2. 缓存未命中，从数据库查询
    user = await user_repo.get_by_id(user_id)
    
    # 3. 写入缓存
    await redis.hmset(cache_key, user.dict())
    await redis.expire(cache_key, 3600)
    
    return user
```

#### Write-Through Pattern (余额更新)
```python
async def update_balance(user_id: str, amount: float):
    # 1. 更新数据库
    await user_repo.update_balance(user_id, amount)
    
    # 2. 更新缓存
    cache_key = f"user:{user_id}"
    await redis.hincrbyfloat(cache_key, "balance", amount)
```

#### Token 使用量实时累加
```python
async def record_token_usage(agent_id: str, tokens: int, cost: float):
    month = datetime.now().strftime("%Y-%m")
    key = f"usage:{agent_id}:{month}"
    
    # 使用 Redis 事务保证原子性
    async with redis.pipeline() as pipe:
        await pipe.hincrby(key, "total_tokens", tokens)
        await pipe.hincrbyfloat(key, "total_cost", cost)
        await pipe.hset(key, "updated_at", datetime.now().isoformat())
        await pipe.expire(key, 2592000)  # 30 天
        await pipe.execute()
    
    # 异步同步到数据库（定时任务）
```

### 6.3 缓存失效策略

```python
# 1. 主动失效（更新数据时）
async def update_vm_status(vm_id: str, status: str):
    await vm_repo.update_status(vm_id, status)
    await redis.delete(f"vm:{vm_id}:status")
    await redis.delete(f"user:{user_id}:vms")

# 2. 被动失效（TTL 过期）
# 所有缓存都设置 TTL

# 3. 定期刷新（热点数据）
async def refresh_hot_data():
    # 每 5 分钟刷新活跃 VM 的状态
    active_vms = await vm_repo.get_active_vms()
    for vm in active_vms:
        status = await libvirt.get_vm_status(vm.id)
        await redis.hmset(f"vm:{vm.id}:status", status)
```

---

## 7. KVM/Libvirt 集成方案

### 7.1 Libvirt 连接管理

```python
# app/infrastructure/vm/libvirt_manager.py
import libvirt
from contextlib import contextmanager
from app.core.config import settings

class LibvirtManager:
    def __init__(self):
        self.uri = settings.LIBVIRT_URI
        self._connection = None
    
    @contextmanager
    def get_connection(self):
        """获取 Libvirt 连接（连接池管理）"""
        conn = None
        try:
            conn = libvirt.open(self.uri)
            yield conn
        finally:
            if conn:
                conn.close()
    
    async def create_vm(self, spec: VMSpec) -> VMInfo:
        """创建虚拟机"""
        with self.get_connection() as conn:
            # 1. 生成 XML 配置
            xml = self._generate_vm_xml(spec)
            
            # 2. 创建域
            domain = conn.defineXML(xml)
            
            # 3. 创建磁盘镜像
            self._create_disk_image(domain, spec.disk_size)
            
            # 4. 启动虚拟机
            domain.create()
            
            # 5. 获取 IP 地址
            ip = await self._wait_for_ip(domain)
            
            return VMInfo(
                id=domain.UUIDString(),
                name=domain.name(),
                ip=ip,
                status="running"
            )
    
    def _generate_vm_xml(self, spec: VMSpec) -> str:
        """生成虚拟机 XML 配置"""
        return f"""
        <domain type='kvm'>
          <name>{spec.name}</name>
          <memory unit='MiB'>{spec.memory}</memory>
          <vcpu>{spec.cpu}</vcpu>
          <os>
            <type arch='x86_64'>hvm</type>
            <boot dev='hd'/>
          </os>
          <devices>
            <disk type='file' device='disk'>
              <driver name='qemu' type='qcow2'/>
              <source file='/var/lib/libvirt/images/{spec.name}.qcow2'/>
              <target dev='vda' bus='virtio'/>
            </disk>
            <interface type='network'>
              <source network='{settings.LIBVIRT_NETWORK_NAME}'/>
              <model type='virtio'/>
            </interface>
            <serial type='pty'/>
            <console type='pty'/>
          </devices>
        </domain>
        """
    
    async def start_vm(self, vm_id: str):
        """启动虚拟机"""
        with self.get_connection() as conn:
            domain = conn.lookupByUUIDString(vm_id)
            domain.create()
    
    async def stop_vm(self, vm_id: str):
        """停止虚拟机"""
        with self.get_connection() as conn:
            domain = conn.lookupByUUIDString(vm_id)
            domain.shutdown()
    
    async def delete_vm(self, vm_id: str):
        """删除虚拟机"""
        with self.get_connection() as conn:
            domain = conn.lookupByUUIDString(vm_id)
            
            # 1. 停止虚拟机
            if domain.isActive():
                domain.destroy()
            
            # 2. 删除磁盘镜像
            disk_path = self._get_disk_path(domain)
            if os.path.exists(disk_path):
                os.remove(disk_path)
            
            # 3. 取消定义
            domain.undefine()
    
    async def get_vm_status(self, vm_id: str) -> dict:
        """获取虚拟机状态"""
        with self.get_connection() as conn:
            domain = conn.lookupByUUIDString(vm_id)
            
            # CPU 使用率
            cpu_stats = domain.getCPUStats(True)[0]
            cpu_percent = (cpu_stats['cpu_time'] / 1000000000) / 60 * 100
            
            # 内存使用率
            mem_stats = domain.memoryStats()
            memory_percent = (mem_stats['actual'] - mem_stats['unused']) / mem_stats['actual'] * 100
            
            return {
                "status": "running" if domain.isActive() else "stopped",
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": await self._get_disk_usage(domain),
            }
```

### 7.2 SSH 自动化部署

```python
# app/infrastructure/vm/ssh_client.py
import asyncssh
from app.core.config import settings

class SSHClient:
    def __init__(self):
        self.key_path = settings.SSH_PRIVATE_KEY_PATH
        self.user = settings.SSH_USER
    
    async def deploy_openclaw(self, ip: str, config: DeployConfig):
        """部署 OpenClaw 到虚拟机"""
        async with asyncssh.connect(
            ip,
            username=self.user,
            client_keys=[self.key_path]
        ) as conn:
            # 1. 更新系统
            await conn.run('apt-get update && apt-get upgrade -y')
            
            # 2. 安装依赖
            await conn.run('apt-get install -y nodejs npm docker.io')
            
            # 3. 安装 OpenClaw
            await conn.run('npm install -g openclaw')
            
            # 4. 初始化配置
            await conn.run('openclaw init')
            
            # 5. 配置 Agent
            for agent_config in config.agents:
                await self._configure_agent(conn, agent_config)
            
            # 6. 启动服务
            await conn.run('systemctl enable openclaw-gateway')
            await conn.run('systemctl start openclaw-gateway')
            
            # 7. 验证
            result = await conn.run('systemctl is-active openclaw-gateway')
            if result.exit_status != 0:
                raise DeployError("OpenClaw 服务启动失败")
    
    async def configure_channel(self, ip: str, channel_config: dict):
        """配置渠道"""
        async with asyncssh.connect(
            ip,
            username=self.user,
            client_keys=[self.key_path]
        ) as conn:
            # 写入配置
            config_json = json.dumps(channel_config)
            await conn.run(f'openclaw config set channels.feishu \'{config_json}\'')
            
            # 重启服务
            await conn.run('systemctl restart openclaw-gateway')
    
    async def get_agent_status(self, ip: str, agent_id: str) -> dict:
        """获取 Agent 状态"""
        async with asyncssh.connect(
            ip,
            username=self.user,
            client_keys=[self.key_path]
        ) as conn:
            result = await conn.run(f'openclaw agent status {agent_id}')
            return json.loads(result.stdout)
```

### 7.3 VM 创建流程

```python
# app/services/vm_service.py
from app.infrastructure.vm.libvirt_manager import LibvirtManager
from app.infrastructure.vm.ssh_client import SSHClient

class VMService:
    def __init__(self):
        self.libvirt = LibvirtManager()
        self.ssh = SSHClient()
    
    async def create_vm(self, user_id: str, plan: Plan, template: AgentTemplate) -> VM:
        """创建虚拟机完整流程"""
        
        # 1. 检查用户余额
        user = await user_repo.get_by_id(user_id)
        if user.balance < plan.price_per_month:
            raise InsufficientBalanceError()
        
        # 2. 创建数据库记录
        vm = await vm_repo.create(
            user_id=user_id,
            plan_id=plan.id,
            name=f"openclaw-{user_id[:8]}",
            cpu=plan.cpu,
            memory=plan.memory,
            disk=plan.disk,
            status="creating"
        )
        
        try:
            # 3. 创建 Libvirt 虚拟机
            vm_spec = VMSpec(
                name=vm.name,
                cpu=plan.cpu,
                memory=plan.memory,
                disk=plan.disk
            )
            vm_info = await self.libvirt.create_vm(vm_spec)
            
            # 4. 更新 IP 地址
            await vm_repo.update(vm.id, ip_address=vm_info.ip, libvirt_domain_name=vm_info.name)
            
            # 5. 部署 OpenClaw
            deploy_config = DeployConfig(
                agents=[template.to_agent_config()]
            )
            await self.ssh.deploy_openclaw(vm_info.ip, deploy_config)
            
            # 6. 扣费
            await billing_service.deduct(user_id, plan.price_per_month, f"订阅套餐：{plan.name}")
            
            # 7. 更新状态
            await vm_repo.update(vm.id, status="running", expires_at=datetime.now() + timedelta(days=30))
            
            return vm
            
        except Exception as e:
            # 失败回滚
            await vm_repo.update(vm.id, status="error")
            await self.libvirt.delete_vm(vm.libvirt_domain_name)
            raise
```

---

## 8. 安全架构设计

### 8.1 认证与授权

```python
# app/core/security.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user
```

### 8.2 限流策略

```python
# app/api/deps.py
from fastapi import Request, HTTPException, status
from app.infrastructure.cache.redis_client import redis

async def rate_limit(request: Request, max_requests: int = 60):
    """限流中间件"""
    ip = request.client.host
    endpoint = request.url.path
    key = f"ratelimit:{ip}:{endpoint}"
    
    current = await redis.get(key)
    if current is None:
        await redis.setex(key, 60, 1)
    elif int(current) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试"
        )
    else:
        await redis.incr(key)
```

### 8.3 数据加密

```python
# app/core/encryption.py
from cryptography.fernet import Fernet
from app.core.config import settings

fernet = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_data(data: str) -> str:
    """加密敏感数据"""
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """解密数据"""
    return fernet.decrypt(encrypted_data.encode()).decode()

# 使用示例：存储 API Key
class Channel(Base):
    config = Column(JSONB)  # {"app_id": "xxx", "app_secret": "encrypted:..."}
    
    def set_config(self, config: dict):
        encrypted_config = {}
        for key, value in config.items():
            if key in ["app_secret", "api_key", "token"]:
                encrypted_config[key] = f"encrypted:{encrypt_data(value)}"
            else:
                encrypted_config[key] = value
        self.config = encrypted_config
    
    def get_config(self) -> dict:
        decrypted_config = {}
        for key, value in self.config.items():
            if isinstance(value, str) and value.startswith("encrypted:"):
                decrypted_config[key] = decrypt_data(value[10:])
            else:
                decrypted_config[key] = value
        return decrypted_config
```

### 8.4 网络安全

```
宿主机防火墙规则：
- 允许：80/443 (Nginx)
- 允许：22 (SSH，仅限管理 IP)
- 允许：5900-5999 (VNC，可选)
- 拒绝：其他所有入站

虚拟机网络：
- 使用 NAT 网络模式
- 虚拟机之间隔离
- 通过宿主机端口转发访问
```

---

## 9. 部署架构

### 9.1 开发环境

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 前端
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

  # 后端
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/openclaw
      - REDIS_URL=redis://redis:6379/0
      - LIBVIRT_URI=qemu+tcp://host.docker.internal/system
    depends_on:
      - postgres
      - redis

  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=openclaw
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### 9.2 生产环境

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - frontend_dist:/usr/share/nginx/html
    depends_on:
      - backend

  # 前端（静态文件）
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    volumes:
      - frontend_dist:/app/dist

  # 后端（多实例）
  backend:
    image: openclaw-vm-platform:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - LIBVIRT_URI=qemu:///system
    depends_on:
      - postgres
      - redis

  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=openclaw
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/postgresql.conf:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf

  # Redis
  redis:
    image: redis:7-alpine
    command: redis-server /etc/redis/redis.conf
    volumes:
      - redis_data:/data
      - ./redis/redis.conf:/etc/redis/redis.conf

  # 定时任务（计费、清理等）
  scheduler:
    image: openclaw-vm-platform:latest
    command: python -m app.scheduler
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - backend

volumes:
  frontend_dist:
  postgres_data:
  redis_data:
```

### 9.3 Nginx 配置

```nginx
# nginx/nginx.conf
upstream backend {
    least_conn;
    server backend:8000;
}

server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 限流
        limit_req zone=api burst=20 nodelay;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        
        # 缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # 限流配置
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}
```

---

## 10. 技术选型说明

### 10.1 后端技术栈

| 技术 | 版本 | 选择理由 |
|-----|------|---------|
| **Python** | 3.11+ | 生态丰富，Libvirt SDK 支持好，AI 集成方便 |
| **FastAPI** | 0.100+ | 高性能，自动文档，类型安全，异步支持 |
| **SQLAlchemy** | 2.0+ | 成熟的 ORM，支持异步，灵活 |
| **Alembic** | 最新 | 数据库迁移工具，与 SQLAlchemy 完美集成 |
| **Pydantic** | 2.0+ | 数据验证，与 FastAPI 深度集成 |
| **Libvirt** | 9.0+ | KVM 官方管理库，功能完整 |
| **asyncssh** | 最新 | 异步 SSH 客户端，性能好 |

### 10.2 前端技术栈

| 技术 | 版本 | 选择理由 |
|-----|------|---------|
| **React** | 18+ | 生态成熟，组件化，团队熟悉 |
| **TypeScript** | 5.0+ | 类型安全，减少运行时错误 |
| **Vite** | 5.0+ | 开发体验好，构建快 |
| **TailwindCSS** | 3.0+ | 快速开发，一致性高 |
| **React Query** | 5.0+ | 数据获取和缓存，减少样板代码 |
| **Zustand** | 4.0+ | 轻量级状态管理 |

### 10.3 基础设施

| 技术 | 版本 | 选择理由 |
|-----|------|---------|
| **PostgreSQL** | 15+ | 可靠性高，功能强大，支持 JSON |
| **Redis** | 7+ | 高性能缓存，支持多种数据结构 |
| **Docker** | 最新 | 容器化部署，环境一致 |
| **Nginx** | 最新 | 高性能反向代理，SSL 终结 |

### 10.4 技术选型权衡

#### 为什么选择 FastAPI 而不是 Node.js/Express？
- **理由 1**: Libvirt Python SDK 更成熟，Node.js 绑定较少
- **理由 2**: Python 生态中 AI/ML 集成更方便（未来可能需要）
- **理由 3**: FastAPI 的自动文档和类型安全提高开发效率
- **权衡**: Node.js 的异步性能略优，但 FastAPI 的异步支持已足够

#### 为什么选择 PostgreSQL 而不是 MySQL？
- **理由 1**: JSONB 支持更好（存储 Agent 配置、元数据）
- **理由 2**: 分区表功能强大（Token 使用记录按月分区）
- **理由 3**: 并发性能和可靠性更高
- **权衡**: MySQL 在简单查询上略快，但 PostgreSQL 更适合复杂场景

#### 为什么选择 KVM 而不是 Docker？
- **理由 1**: 完全隔离，安全性更高
- **理由 2**: 用户需要完整的 VM 控制权
- **理由 3**: 可以运行任意操作系统和服务
- **权衡**: Docker 更轻量，但隔离性不足

---

## 11. 风险与权衡

### 11.1 技术风险

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| **Libvirt 权限问题** | 无法创建 VM | 使用 root 权限运行，配置 AppArmor |
| **并发 VM 操作** | 资源竞争、死锁 | 使用 Redis 分布式锁，队列化操作 |
| **SSH 连接超时** | 部署失败 | 重试机制，超时配置，健康检查 |
| **磁盘空间不足** | VM 创建失败 | 监控磁盘使用，自动清理，扩容告警 |
| **网络 IP 耗尽** | 无法分配 IP | IP 池管理，NAT 配置，定期回收 |

### 11.2 架构权衡

| 决策 | 优势 | 劣势 |
|-----|------|------|
| **单体架构** | 简单、开发快、部署简单 | 扩展性受限、耦合度高 |
| **预充值模式** | 资金流好、风险低 | 用户体验略差、需要提醒机制 |
| **平台提供模型** | 统一管理、成本可控 | 单点故障、扩展性受限 |
| **自建 KVM** | 成本低、可控性高 | 运维复杂、扩展性差 |

### 11.3 未来演进路径

**短期（3-6 个月）**：
- 优化 VM 创建速度（镜像缓存、并行部署）
- 引入消息队列（Celery）异步化耗时操作
- 增加更多云提供商支持（阿里云、腾讯云）

**中期（6-12 个月）**：
- 微服务拆分（用户服务、计费服务、VM 服务）
- 引入 Kubernetes 管理平台服务
- 多区域部署

**长期（12+ 个月）**：
- 混合云架构（自建 + 公有云）
- Serverless 计费（按实际使用量）
- AI 运维自动化

---

## 12. 下一步行动

### 12.1 立即行动（本周）

1. **环境准备**
   - [ ] 配置开发环境（Docker、PostgreSQL、Redis）
   - [ ] 测试 Libvirt 连接
   - [ ] 准备基础镜像

2. **数据库初始化**
   - [ ] 执行数据库迁移脚本
   - [ ] 插入初始数据（套餐、模板）
   - [ ] 配置分区表

3. **API 开发**
   - [ ] 实现用户认证模块
   - [ ] 实现 VM CRUD 接口
   - [ ] 实现 Libvirt 集成

### 12.2 交给 Coder 的任务

```markdown
@coder 请按以下顺序开发：

1. **用户系统** (P0)
   - 注册、登录、JWT 认证
   - 用户信息管理、余额充值

2. **VM 管理** (P0)
   - Libvirt 集成
   - VM 创建、启停、删除
   - SSH 自动化部署

3. **Agent 配置** (P0)
   - Agent 模板管理
   - Agent CRUD
   - 模型配置

4. **渠道配置** (P0)
   - 飞书配置流程
   - 凭证验证
   - 自动化配置

5. **计费系统** (P0)
   - 余额管理
   - Token 统计
   - 消费记录

请参考本文档第 4 章的 API 规范和第 5 章的数据库模型。
```

---

**架构设计完成 ✅**

**交付物**：
- ✅ 完整的系统架构设计
- ✅ 详细的 API 接口规范（8 个模块，50+ 接口）
- ✅ 数据库模型设计（10 张表 + 视图 + 分区）
- ✅ 缓存策略设计
- ✅ KVM/Libvirt 集成方案
- ✅ 安全架构设计
- ✅ 部署架构设计
- ✅ 技术选型说明

**下一步**：交给 **@coder** 开始实现后端 API，交给 **@frontenddev** 实现前端界面。

---

_文档版本: v3.0_  
_最后更新: 2026-03-21_  
_架构师: Architect_
