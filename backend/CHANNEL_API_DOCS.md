# 渠道配置 API 文档

## 概述
实现了完整的渠道配置 API，支持飞书（Feishu）和 Telegram 两种渠道的配置、管理和测试。

## 实现的端点

### 1. 创建飞书渠道
**POST** `/api/v1/channels/feishu`

**请求体：**
```json
{
  "agent_id": "uuid",
  "config": {
    "app_id": "cli_xxx",
    "app_secret": "xxx"
  }
}
```

**功能：**
- 验证飞书 App ID 和 App Secret
- 调用飞书 API 验证凭证
- 生成 webhook URL
- 返回配置步骤指南

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": "channel-uuid",
    "agent_id": "agent-uuid",
    "type": "feishu",
    "status": "configuring",
    "config": {
      "app_id": "cli_xxx",
      "validated": true
    },
    "configuration_steps": [
      {
        "step": 1,
        "title": "Configure Event Subscription",
        "webhook_url": "https://your-domain.com/webhooks/feishu/channel-id",
        "completed": false
      }
    ]
  },
  "message": "Feishu channel created successfully. Please follow the configuration steps."
}
```

---

### 2. 创建 Telegram 渠道
**POST** `/api/v1/channels/telegram`

**请求体：**
```json
{
  "agent_id": "uuid",
  "config": {
    "bot_token": "123456:ABC",
    "allowed_chat_ids": [123456789]
  }
}
```

**功能：**
- 验证 Telegram Bot Token 格式
- 调用 Telegram API 验证 Bot
- 配置允许的聊天 ID
- 返回配置步骤指南

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": "channel-uuid",
    "agent_id": "agent-uuid",
    "type": "telegram",
    "status": "configuring",
    "config": {
      "bot_info": {
        "bot_username": "your_bot",
        "bot_name": "Your Bot"
      },
      "allowed_chat_ids": [123456789],
      "validated": true
    },
    "configuration_steps": [...]
  }
}
```

---

### 3. 渠道列表
**GET** `/api/v1/channels`

**查询参数：**
- `agent_id` (可选): 按 Agent ID 过滤
- `status_filter` (可选): 按状态过滤
- `type_filter` (可选): 按类型过滤
- `page`: 页码
- `page_size`: 每页数量

**功能：**
- 列出用户的所有渠道
- 支持多维度过滤
- 分页支持
- 自动隐藏敏感信息（app_secret、bot_token）

**响应示例：**
```json
{
  "success": true,
  "data": {
    "items": [...],
    "total": 10,
    "page": 1,
    "page_size": 20,
    "pages": 1
  }
}
```

---

### 4. 渠道详情
**GET** `/api/v1/channels/{id}`

**功能：**
- 获取单个渠道的详细信息
- 包含配置步骤和测试状态
- 自动隐藏敏感信息

---

### 5. 渠道状态检查
**GET** `/api/v1/channels/{id}/status`

**功能：**
- 实时检查渠道连接状态
- 验证飞书/Telegram 凭证有效性
- 自动更新渠道状态（active/error）

**响应示例：**
```json
{
  "success": true,
  "data": {
    "channel_id": "uuid",
    "type": "telegram",
    "status": "active",
    "is_connected": true,
    "details": {
      "bot_username": "your_bot",
      "validated": true
    }
  }
}
```

---

### 6. 发送测试消息
**POST** `/api/v1/channels/{id}/test`

**请求体（可选）：**
```json
{
  "message": "Custom test message"
}
```

**功能：**
- 通过渠道发送测试消息
- 验证渠道配置是否正确
- 更新测试状态和时间戳

---

### 7. 删除渠道
**DELETE** `/api/v1/channels/{id}`

**功能：**
- 删除指定渠道
- 验证权限
- 级联删除相关数据

---

## 安全特性

1. **权限验证**
   - 所有端点都需要用户认证
   - 验证渠道所属的 Agent 是否属于当前用户
   - 使用 UUID 验证防止枚举攻击

2. **敏感信息保护**
   - 响应中自动移除 `app_secret` 和 `bot_token`
   - 数据库中的敏感字段需要加密（TODO）

3. **输入验证**
   - 使用 Pydantic 进行严格的输入验证
   - 飞书 App ID 格式验证（必须以 `cli_` 开头）
   - Telegram Bot Token 格式验证

4. **外部 API 验证**
   - 实时调用飞书/Telegram API 验证凭证
   - 超时处理（10秒）
   - 错误处理和友好提示

---

## 数据模型

### ChannelStatus
- `pending`: 待配置
- `configuring`: 配置中
- `active`: 已激活
- `error`: 错误状态

### ChannelType
- `feishu`: 飞书
- `telegram`: Telegram
- `whatsapp`: WhatsApp（预留）
- `webchat`: 网页聊天（预留）

---

## 配置步骤

### 飞书渠道配置步骤
1. 配置事件订阅（添加 webhook URL）
2. 启用消息接收事件
3. 发送测试消息验证

### Telegram 渠道配置步骤
1. 设置 webhook
2. 配置允许的聊天 ID
3. 发送测试消息验证

---

## 实现细节

### 1. 飞书验证
```python
async def validate_feishu_credentials(app_id: str, app_secret: str) -> dict:
    # 调用飞书 API 获取 tenant_access_token
    # POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
```

### 2. Telegram 验证
```python
async def validate_telegram_bot_token(bot_token: str) -> dict:
    # 调用 Telegram API 获取 Bot 信息
    # GET https://api.telegram.org/bot{token}/getMe
```

### 3. Webhook URL 生成
```python
def generate_webhook_url(channel_id: str, channel_type: str) -> str:
    # 生成格式: {BASE_URL}/webhooks/{type}/{id}
```

---

## 测试

### 单元测试
```bash
cd backend
source venv/bin/activate
python test_channels_api.py
```

### 集成测试（需要完整环境）
```bash
# 1. 启动数据库
# 2. 运行迁移
# 3. 启动 Redis
# 4. 启动后端服务
# 5. 运行 pytest
```

---

## TODO / 后续改进

1. **安全增强**
   - [ ] 加密存储敏感字段（app_secret、bot_token）
   - [ ] 添加速率限制
   - [ ] 添加操作审计日志

2. **功能完善**
   - [ ] 实现真实的测试消息发送（目前只验证凭证）
   - [ ] 实现渠道更新接口
   - [ ] 添加渠道统计数据（消息数、成功率等）
   - [ ] 支持 WhatsApp 和 Webchat 渠道

3. **监控与告警**
   - [ ] 添加渠道健康检查定时任务
   - [ ] 渠道异常告警
   - [ ] 性能监控

4. **文档完善**
   - [ ] 添加 OpenAPI 示例
   - [ ] 创建集成测试
   - [ ] 编写用户指南

---

## 依赖项

- FastAPI
- SQLAlchemy
- Pydantic
- httpx（用于外部 API 调用）
- PostgreSQL（JSONB 字段）

---

## 变更日志

### v1.0.0 (2026-03-23)
- ✅ 实现飞书渠道配置 API
- ✅ 实现 Telegram 渠道配置 API
- ✅ 实现渠道列表、详情、状态检查
- ✅ 实现测试消息发送
- ✅ 实现渠道删除
- ✅ 添加完整的权限验证
- ✅ 添加外部 API 验证
- ✅ 添加配置步骤指南
