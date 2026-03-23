# 计费系统 API 文档

## 概述

计费系统 API 提供了完整的用户计费、使用记录查询和充值功能。

**Base URL**: `/api/v1/billing`

**认证**: 所有端点需要 JWT Token 认证（Bearer Token）

---

## API 端点

### 1. 使用记录查询

**GET** `/api/v1/billing/usage`

查询当前用户的 Token 使用记录。

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | datetime | 否 | 起始日期（ISO 格式） |
| end_date | datetime | 否 | 结束日期（ISO 格式） |
| agent_id | string (UUID) | 否 | 筛选指定 Agent |
| page | integer | 否 | 页码（默认 1） |
| page_size | integer | 否 | 每页数量（默认 20，最大 100） |

#### 响应示例

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "agent_id": "uuid",
        "agent_name": "My Agent",
        "model": "gpt-4",
        "prompt_tokens": 1000,
        "completion_tokens": 500,
        "total_tokens": 1500,
        "cost": 0.15,
        "created_at": "2026-03-23T08:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
    "pages": 1
  }
}
```

---

### 2. 使用统计

**GET** `/api/v1/billing/stats`

获取指定时间段的使用统计信息。

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| period | string | 否 | 时间周期：`day`、`week`、`month`（默认 month） |

#### 响应示例

```json
{
  "success": true,
  "data": {
    "total_tokens": 1000000,
    "total_cost": 10.50,
    "by_agent": [
      {
        "agent_id": "uuid",
        "agent_name": "My Agent",
        "tokens": 500000,
        "cost": 5.25
      }
    ],
    "by_model": [
      {
        "model": "gpt-4",
        "tokens": 800000,
        "cost": 8.00
      },
      {
        "model": "gpt-3.5-turbo",
        "tokens": 200000,
        "cost": 2.50
      }
    ],
    "period": "month",
    "start_date": "2026-02-23T00:00:00",
    "end_date": "2026-03-23T08:00:00"
  }
}
```

---

### 3. 余额查询

**GET** `/api/v1/billing/balance`

查询当前用户的账户余额信息。

#### 响应示例

```json
{
  "success": true,
  "data": {
    "balance": 100.00,
    "pending": 0.00,
    "total_recharged": 200.00,
    "total_used": 100.00
  }
}
```

#### 字段说明

- `balance`: 当前可用余额
- `pending`: 待处理金额（正在充值中的金额）
- `total_recharged`: 累计充值金额
- `total_used`: 累计使用金额

---

### 4. 订单列表

**GET** `/api/v1/billing/orders`

查询当前用户的订单历史。

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_type | string | 否 | 订单类型：`recharge`、`subscription`、`token_usage`、`disk_expansion`、`backup` |
| status | string | 否 | 订单状态：`pending`、`completed`、`failed`、`refunded` |
| page | integer | 否 | 页码（默认 1） |
| page_size | integer | 否 | 每页数量（默认 20，最大 100） |

#### 响应示例

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "type": "recharge",
        "amount": 100.00,
        "balance_before": 50.00,
        "balance_after": 150.00,
        "description": "Account recharge via alipay",
        "status": "completed",
        "payment_method": "alipay",
        "created_at": "2026-03-23T08:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
    "pages": 1
  }
}
```

---

### 5. 充值

**POST** `/api/v1/billing/recharge`

创建充值订单。

#### 请求体

```json
{
  "amount": 100.00,
  "payment_method": "alipay"
}
```

#### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| amount | float | 是 | 充值金额（必须大于 0） |
| payment_method | string | 是 | 支付方式：`alipay`、`wechat`、`bank_transfer` |

#### 响应示例

```json
{
  "success": true,
  "data": {
    "order_id": "uuid",
    "amount": 100.00,
    "balance_before": 100.00,
    "balance_after": 200.00,
    "status": "completed",
    "payment_url": "https://payment.example.com/pay/uuid",
    "payment_method": "alipay"
  },
  "message": "Recharge order created successfully"
}
```

**注意**: 当前实现为 Mock 模式，充值会立即完成。在生产环境中，需要集成真实的支付网关。

---

## 错误响应

所有错误响应遵循统一格式：

```json
{
  "success": false,
  "message": "Error description",
  "error": "ERROR_CODE"
}
```

### 常见错误码

| HTTP 状态码 | 错误信息 | 说明 |
|------------|---------|------|
| 400 | Invalid payment method | 支付方式无效 |
| 400 | Invalid order type | 订单类型无效 |
| 400 | Invalid order status | 订单状态无效 |
| 400 | Invalid agent ID format | Agent ID 格式错误 |
| 401 | Could not validate credentials | 未认证或 Token 无效 |
| 403 | User account is not active | 用户账户未激活 |

---

## 实现要点

### 1. 权限控制

- 所有端点都需要 JWT Token 认证
- 用户只能查看和操作自己的数据
- 通过 `current_user` 依赖注入获取当前用户

### 2. 性能优化

- 使用 SQLAlchemy 的 `func.sum` 进行聚合查询
- 避免 N+1 查询（批量获取 Agent 名称）
- 使用索引优化查询（user_id、created_at 等字段）

### 3. 数据一致性

- 使用数据库事务确保余额更新的原子性
- Order 表记录每次余额变动的前后值

### 4. 统计查询

- 支持按 Agent 分组统计
- 支持按 Model 分组统计
- 支持按时间周期筛选（day/week/month）

---

## 数据库表结构

### orders 表

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    vm_id UUID REFERENCES vms(id),
    type VARCHAR(20),  -- recharge, subscription, token_usage, disk_expansion, backup
    amount DECIMAL(10, 2),
    balance_before DECIMAL(10, 2),
    balance_after DECIMAL(10, 2),
    description TEXT,
    extra_data JSONB,
    status VARCHAR(20),  -- pending, completed, failed, refunded
    payment_method VARCHAR(20),
    payment_transaction_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE
);
```

### token_usage 表

```sql
CREATE TABLE token_usage (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    vm_id UUID REFERENCES vms(id),
    user_id UUID REFERENCES users(id),
    model VARCHAR(100),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost DECIMAL(10, 6),
    request_id VARCHAR(255),
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE
);
```

### users 表（余额字段）

```sql
ALTER TABLE users ADD COLUMN balance DECIMAL(10, 2) DEFAULT 0.00;
```

---

## 使用示例

### cURL 示例

```bash
# 获取余额
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/billing/balance

# 查询使用记录
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/billing/usage?page=1&page_size=20"

# 获取使用统计
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/billing/stats?period=month"

# 创建充值订单
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100.00, "payment_method": "alipay"}' \
  http://localhost:8000/api/v1/billing/recharge
```

---

## 未来改进

1. **真实支付集成**: 集成支付宝、微信支付等真实支付网关
2. **余额预警**: 添加余额不足提醒功能
3. **自动充值**: 支持余额不足时自动充值
4. **发票管理**: 添加发票开具功能
5. **优惠码**: 支持优惠码和折扣功能
6. **详细报表**: 提供更详细的计费报表和导出功能

---

## 版本历史

- **v1.0.0** (2026-03-23): 初始实现，包含 5 个核心 API 端点
