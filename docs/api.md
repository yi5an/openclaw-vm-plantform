# OpenClaw VM Platform - API 文档

## 概述

OpenClaw VM Platform API 是基于 FastAPI 构建的 RESTful API，提供虚拟机管理、用户认证、计费等功能。

- **Base URL**: `http://localhost:8000/api/v1`
- **认证方式**: JWT Bearer Token
- **内容格式**: JSON
- **API 版本**: v1

## 认证

### 注册

**POST** `/auth/register`

创建新用户账户。

#### 请求体

```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "username": "myusername"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | string | 是 | 邮箱地址（格式验证） |
| password | string | 是 | 密码（8-100字符） |
| username | string | 是 | 用户名（3-100字符） |

#### 成功响应 (201)

```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "myusername",
    "balance": 0.0,
    "role": "user",
    "created_at": "2026-03-22T10:30:00"
  }
}
```

#### 错误响应

**409 Conflict** - 邮箱或用户名已存在
```json
{
  "success": false,
  "error": {
    "code": "CONFLICT_ERROR",
    "message": "Email already registered"
  }
}
```

---

### 登录

**POST** `/auth/login`

用户登录并获取访问令牌。

#### 请求体 (OAuth2 Form)

```
username=user@example.com
password=securepassword123
```

> 注意：`username` 字段实际应填入邮箱地址

#### 成功响应 (200)

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

#### 错误响应

**401 Unauthorized** - 凭据无效
```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED_ERROR",
    "message": "Incorrect email or password"
  }
}
```

---

### 刷新令牌

**POST** `/auth/refresh`

使用 refresh token 获取新的访问令牌。

#### 请求体

```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### 成功响应 (200)

```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

---

## 用户管理

### 获取当前用户信息

**GET** `/users/me`

获取当前登录用户的详细信息。

#### 请求头

```
Authorization: Bearer {access_token}
```

#### 成功响应 (200)

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "myusername",
    "balance": 150.50,
    "role": "user",
    "created_at": "2026-03-22T10:30:00",
    "updated_at": "2026-03-22T12:45:00"
  }
}
```

---

### 更新用户信息

**PATCH** `/users/me`

更新当前用户的用户名。

#### 请求头

```
Authorization: Bearer {access_token}
```

#### 请求体

```json
{
  "username": "newusername"
}
```

#### 成功响应 (200)

```json
{
  "success": true,
  "message": "User updated successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "newusername",
    "balance": 150.50,
    "role": "user",
    "created_at": "2026-03-22T10:30:00",
    "updated_at": "2026-03-22T13:00:00"
  }
}
```

---

### 充值

**POST** `/users/me/recharge`

为账户余额充值（支付集成占位符）。

#### 请求头

```
Authorization: Bearer {access_token}
```

#### 请求体

```json
{
  "amount": 100.00,
  "payment_method": "alipay"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| amount | number | 是 | 充值金额（必须大于0） |
| payment_method | string | 是 | 支付方式（alipay/wechat/bank） |

#### 成功响应 (200)

```json
{
  "success": true,
  "message": "Recharge order created",
  "data": {
    "order_id": "placeholder-order-id",
    "amount": 100.00,
    "payment_url": "https://payment.example.com/pay/placeholder",
    "status": "pending"
  }
}
```

---

## 虚拟机管理

### 获取套餐列表

**GET** `/vms/plans`

获取所有可用的虚拟机套餐。

#### 成功响应 (200)

```json
{
  "success": true,
  "data": [
    {
      "id": "plan-basic",
      "name": "基础版",
      "description": "适合个人使用",
      "cpu": 1,
      "memory": 2048,
      "disk": 20,
      "max_agents": 3,
      "max_channels": 5,
      "price_per_month": 99.00,
      "features": ["Telegram", "WhatsApp", "基础监控"]
    },
    {
      "id": "plan-pro",
      "name": "专业版",
      "description": "适合团队使用",
      "cpu": 2,
      "memory": 4096,
      "disk": 50,
      "max_agents": 10,
      "max_channels": 20,
      "price_per_month": 299.00,
      "features": ["所有渠道", "高级监控", "自动备份", "优先支持"]
    }
  ]
}
```

---

### 创建虚拟机

**POST** `/vms`

创建新的虚拟机实例。

#### 请求头

```
Authorization: Bearer {access_token}
```

#### 请求体

```json
{
  "name": "my-openclaw-vm",
  "plan_id": "plan-basic",
  "agent_template_id": "template-123",
  "region": "default"
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | VM 名称（3-100字符） |
| plan_id | string | 是 | 套餐ID |
| agent_template_id | string | 否 | Agent模板ID |
| region | string | 否 | 区域（默认：default） |

#### 成功响应 (201)

```json
{
  "success": true,
  "message": "VM creation initiated",
  "data": {
    "id": "vm-550e8400-e29b-41d4-a716-446655440000",
    "name": "my-openclaw-vm",
    "status": "creating",
    "ip_address": null,
    "plan": {
      "id": "plan-basic",
      "name": "基础版",
      "description": "适合个人使用",
      "cpu": 1,
      "memory": 2048,
      "disk": 20,
      "max_agents": 3,
      "max_channels": 5,
      "price_per_month": 99.00,
      "features": ["Telegram", "WhatsApp", "基础监控"]
    },
    "created_at": "2026-03-22T14:00:00",
    "expires_at": "2026-04-22T14:00:00"
  }
}
```

#### 错误响应

**404 Not Found** - 套餐不存在
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND_ERROR",
    "message": "Plan not found: plan-xyz"
  }
}
```

**402 Payment Required** - 余额不足
```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_BALANCE_ERROR",
    "message": "Insufficient balance",
    "details": {
      "required": 99.00,
      "available": 50.00
    }
  }
}
```

**409 Conflict** - VM名称已存在
```json
{
  "success": false,
  "error": {
    "code": "CONFLICT_ERROR",
    "message": "VM with this name already exists"
  }
}
```

---

### 获取虚拟机列表

**GET** `/vms`

获取当前用户的所有虚拟机。

#### 请求头

```
Authorization: Bearer {access_token}
```

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status_filter | string | 否 | 按状态过滤 |
| page | int | 否 | 页码（默认：1） |
| page_size | int | 否 | 每页数量（默认：20） |

#### 成功响应 (200)

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "vm-550e8400-e29b-41d4-a716-446655440000",
        "name": "my-openclaw-vm",
        "status": "running",
        "ip_address": "192.168.1.100",
        "plan": {
          "id": "plan-basic",
          "name": "基础版",
          "description": "适合个人使用",
          "cpu": 1,
          "memory": 2048,
          "disk": 20,
          "max_agents": 3,
          "max_channels": 5,
          "price_per_month": 99.00,
          "features": ["Telegram", "WhatsApp", "基础监控"]
        },
        "created_at": "2026-03-22T14:00:00",
        "expires_at": "2026-04-22T14:00:00"
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 20,
    "pages": 1
  }
}
```

---

### 获取虚拟机详情

**GET** `/vms/{vm_id}`

获取指定虚拟机的详细信息。

#### 请求头

```
Authorization: Bearer {access_token}
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| vm_id | string | 虚拟机ID |

#### 成功响应 (200)

```json
{
  "success": true,
  "data": {
    "id": "vm-550e8400-e29b-41d4-a716-446655440000",
    "name": "my-openclaw-vm",
    "status": "running",
    "ip_address": "192.168.1.100",
    "plan": {
      "id": "plan-basic",
      "name": "基础版",
      "description": "适合个人使用",
      "cpu": 1,
      "memory": 2048,
      "disk": 20,
      "max_agents": 3,
      "max_channels": 5,
      "price_per_month": 99.00,
      "features": ["Telegram", "WhatsApp", "基础监控"]
    },
    "expires_at": "2026-04-22T14:00:00",
    "created_at": "2026-03-22T14:00:00",
    "updated_at": "2026-03-22T14:30:00",
    "usage": {
      "cpu_percent": 25.5,
      "memory_percent": 45.2,
      "disk_percent": 30.0,
      "network_in_bytes": 1048576,
      "network_out_bytes": 2097152
    }
  }
}
```

#### 错误响应

**404 Not Found** - VM不存在
```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND_ERROR",
    "message": "VM not found: vm-xyz"
  }
}
```

**403 Forbidden** - 无权限访问
```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN_ERROR",
    "message": "You don't have access to this VM"
  }
}
```

---

### 启动虚拟机

**POST** `/vms/{vm_id}/start`

启动指定的虚拟机。

#### 请求头

```
Authorization: Bearer {access_token}
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| vm_id | string | 虚拟机ID |

#### 成功响应 (200)

```json
{
  "success": true,
  "message": "VM start operation initiated",
  "data": {
    "id": "vm-550e8400-e29b-41d4-a716-446655440000",
    "status": "starting",
    "message": "虚拟机正在启动"
  }
}
```

---

### 停止虚拟机

**POST** `/vms/{vm_id}/stop`

停止指定的虚拟机。

#### 请求头

```
Authorization: Bearer {access_token}
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| vm_id | string | 虚拟机ID |

#### 成功响应 (200)

```json
{
  "success": true,
  "message": "VM stop operation initiated",
  "data": {
    "id": "vm-550e8400-e29b-41d4-a716-446655440000",
    "status": "stopping",
    "message": "虚拟机正在停止"
  }
}
```

---

### 删除虚拟机

**DELETE** `/vms/{vm_id}`

删除指定的虚拟机（⚠️ 不可恢复，所有数据将被清除）。

#### 请求头

```
Authorization: Bearer {access_token}
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| vm_id | string | 虚拟机ID |

#### 成功响应 (200)

```json
{
  "success": true,
  "message": "VM deletion initiated",
  "data": {
    "id": "vm-550e8400-e29b-41d4-a716-446655440000",
    "status": "deleting",
    "message": "虚拟机正在删除，所有数据将被清除"
  }
}
```

---

### 续费虚拟机

**POST** `/vms/{vm_id}/renew`

为虚拟机续费。

#### 请求头

```
Authorization: Bearer {access_token}
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| vm_id | string | 虚拟机ID |

#### 请求体

```json
{
  "months": 3
}
```

#### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| months | int | 是 | 续费月数（1-12） |

#### 成功响应 (200)

```json
{
  "success": true,
  "message": "VM renewed successfully",
  "data": {
    "id": "vm-550e8400-e29b-41d4-a716-446655440000",
    "expires_at": "2026-07-22T14:00:00",
    "cost": 297.00,
    "new_balance": 103.50
  }
}
```

---

## 通用错误码

| HTTP状态码 | 错误码 | 说明 |
|-----------|--------|------|
| 400 | BAD_REQUEST_ERROR | 请求参数错误 |
| 401 | UNAUTHORIZED_ERROR | 未授权访问 |
| 403 | FORBIDDEN_ERROR | 无权限访问 |
| 404 | NOT_FOUND_ERROR | 资源不存在 |
| 409 | CONFLICT_ERROR | 资源冲突 |
| 402 | INSUFFICIENT_BALANCE_ERROR | 余额不足 |
| 422 | VALIDATION_ERROR | 数据验证失败 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 错误响应格式

所有错误响应遵循统一格式：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      "field": "additional information"
    }
  }
}
```

---

## 速率限制

API 实施速率限制以防止滥用：

- **默认限制**: 60 请求/分钟
- **认证端点**: 10 请求/分钟

超出限制时返回 **429 Too Many Requests**：

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "details": {
      "retry_after": 60
    }
  }
}
```

---

## API 端点

完整的交互式 API 文档可通过以下地址访问：

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

---

## WebSocket 端点（计划中）

### 实时监控

**WebSocket** `/ws/vm/{vm_id}/monitor`

实时接收虚拟机监控数据（开发中）。

---

## 最佳实践

1. **认证**: 每次请求都应包含有效的 Bearer Token
2. **错误处理**: 始终检查 `success` 字段，妥善处理错误
3. **令牌刷新**: 在 `expires_in` 时间前使用 refresh token 刷新
4. **分页**: 对于列表接口，使用分页避免大量数据传输
5. **幂等性**: 创建和更新操作设计为幂等，使用唯一标识符

---

## 版本控制

API 遵循语义化版本控制。当前版本：**v1**

破坏性变更将导致主版本号升级（v2, v3...），现有版本将继续维护一段时间。

---

_最后更新: 2026-03-22_
_文档版本: 1.0.0_
