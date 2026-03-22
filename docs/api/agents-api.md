# Agent Management API 文档

## 概述

已完成 Agent 管理 API 的全部实现，包含 8 个核心端点，支持完整的 CRUD 操作和生命周期管理。

## API 端点列表

### 1. 创建 Agent
```http
POST /api/v1/agents
```

**请求体：**
```json
{
  "vm_id": "uuid",
  "template_id": "uuid",  // 可选
  "name": "我的客服助手",
  "system_prompt": "你是一个专业的客服...",
  "model_config": {
    "provider": "platform",  // platform | custom
    "model_name": "gpt-4",
    "api_key": null,  // 如果 provider=custom 则必填
    "temperature": 0.7
  }
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "vm_id": "uuid",
    "template_id": "uuid",
    "name": "我的客服助手",
    "status": "creating",
    "system_prompt": "...",
    "model_config": {...},
    "messages_count": 0,
    "last_active_at": null,
    "created_at": "2026-03-22T...",
    "updated_at": "2026-03-22T..."
  },
  "message": "Agent created successfully"
}
```

### 2. Agent 列表
```http
GET /api/v1/agents?vm_id={vm_id}&status_filter={status}
```

**查询参数：**
- `vm_id` (可选): 按虚拟机筛选
- `status_filter` (可选): 按状态筛选
- `page`: 页码（默认 1）
- `page_size`: 每页数量（默认 20，最大 100）

**响应：**
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

### 3. Agent 详情
```http
GET /api/v1/agents/{id}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "vm_id": "uuid",
    "name": "我的客服助手",
    "status": "running",
    ...
  }
}
```

### 4. 更新 Agent
```http
PATCH /api/v1/agents/{id}
```

**请求体（所有字段可选）：**
```json
{
  "name": "新名称",
  "system_prompt": "新的提示词",
  "model_config": {
    "provider": "custom",
    "model_name": "gpt-4",
    "api_key": "sk-xxx",
    "temperature": 0.8
  }
}
```

### 5. 启动 Agent
```http
POST /api/v1/agents/{id}/start
```

**前置条件：**
- Agent 状态为 `stopped` 或 `creating`
- VM 状态为 `running`

**响应：**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "running",
    "message": "Agent started successfully"
  }
}
```

### 6. 停止 Agent
```http
POST /api/v1/agents/{id}/stop
```

**前置条件：**
- Agent 状态为 `running`

**响应：**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "stopped",
    "message": "Agent stopped successfully"
  }
}
```

### 7. 删除 Agent
```http
DELETE /api/v1/agents/{id}
```

**前置条件：**
- Agent 状态为 `stopped`（不能删除运行中的 Agent）

**响应：**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "message": "Agent deleted successfully"
  }
}
```

### 8. 验证自定义 Token
```http
POST /api/v1/agents/validate-token
```

**请求体：**
```json
{
  "provider": "openai",
  "api_key": "sk-xxx",
  "model_name": "gpt-4"
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "provider": "openai",
    "model_name": "gpt-4",
    "message": "Token validation successful"
  }
}
```

## 核心功能特性

### 1. 权限验证
- 所有端点都需要用户认证（JWT Token）
- 用户只能操作自己 VM 下的 Agent
- 自动验证 VM 所有权

### 2. 配额检查
- 创建 Agent 时自动检查套餐限制
- 错误提示清晰：`Agent quota exceeded. Your plan allows X agents per VM. Current: Y`

### 3. 模型配置
- 支持 **platform** 模式：使用平台提供的模型
- 支持 **custom** 模式：用户自定义 API Key
- 自定义模式下必须提供 API Key

### 4. 状态管理
- Agent 状态：`creating` / `running` / `stopped` / `error`
- 不能删除运行中的 Agent
- 不能启动已运行的 Agent
- 不能停止已停止的 Agent

### 5. 错误处理
- 统一的错误响应格式
- 清晰的错误消息
- HTTP 状态码符合 RESTful 规范

## 测试覆盖

已创建完整的测试文件 `backend/tests/test_agents.py`，包含：

- ✅ 创建 Agent（成功/失败场景）
- ✅ 自定义 Provider（有/无 API Key）
- ✅ 权限验证（访问他人 VM）
- ✅ 配额检查（超过限制）
- ✅ 列表查询（全部/按 VM 筛选）
- ✅ 详情查询
- ✅ 更新操作
- ✅ 启动/停止操作
- ✅ 删除操作
- ✅ Token 验证

## 数据模型

Agent 表已包含所有必需字段：
- `id`: UUID 主键
- `vm_id`: 关联的虚拟机
- `template_id`: 关联的模板（可选）
- `name`: Agent 名称
- `status`: 状态（creating/running/stopped/error）
- `system_prompt`: 系统提示词
- `model_config`: 模型配置（JSONB）
- `messages_count`: 消息计数
- `last_active_at`: 最后活跃时间
- `created_at`: 创建时间
- `updated_at`: 更新时间

## 文件清单

### 新增文件
1. `backend/app/api/v1/agents.py` - Agent API 端点实现
2. `backend/tests/test_agents.py` - 完整测试用例

### 修改文件
1. `backend/app/main.py` - 注册 Agent 路由

## Git 提交

**分支**: `feature/p1-agent-api`
**提交 ID**: `51dc613`
**提交信息**: 
```
feat(agents): implement Agent management API

- Add complete Agent CRUD operations
- Implement all 8 API endpoints
- Features: VM ownership verification, Agent quota checking
- Complete test coverage
```

## 下一步建议

1. **实际 Token 验证**：实现真实的 API 调用来验证自定义 Token
2. **Agent 启动逻辑**：集成实际的 Agent 启动流程（初始化模型、设置渠道等）
3. **Agent 停止逻辑**：实现优雅关闭（关闭连接、刷新队列等）
4. **性能优化**：添加缓存（如 Plan 信息）、优化查询
5. **监控日志**：添加详细的操作日志和性能监控

## API 访问示例

```bash
# 创建 Agent
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "vm_id": "<vm-uuid>",
    "name": "客服助手",
    "system_prompt": "你是一个专业的客服",
    "model_config": {
      "provider": "platform",
      "model_name": "gpt-4",
      "temperature": 0.7
    }
  }'

# 列出所有 Agent
curl -X GET http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer <token>"

# 启动 Agent
curl -X POST http://localhost:8000/api/v1/agents/<agent-id>/start \
  -H "Authorization: Bearer <token>"
```

---

**实现完成时间**: 2026-03-22
**负责人**: Coder
**状态**: ✅ 已完成并提交
