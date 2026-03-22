# OpenClaw VM Platform - Backend

FastAPI-based backend for OpenClaw VM Platform - 虚拟机租赁平台

## 🎯 已完成功能

### P0 优先级（已完成）

#### 1. ✅ 用户认证系统
- 用户注册（邮箱 + 用户名 + 密码）
- 用户登录（JWT 认证）
- Token 刷新机制
- 密码加密（bcrypt）
- 用户信息管理
- 余额充值（接口预留）

#### 2. ✅ 实例管理 API
- 套餐列表查询
- VM 创建（基础框架）
- VM 列表查询（分页）
- VM 详情查询
- VM 启动/停止/删除
- VM 续费
- 余额检查

#### 3. ✅ 数据库模型
- 完整的 ORM 模型（10 张表）
- 枚举类型定义
- 关系映射
- 索引优化

#### 4. ✅ 基础设施
- PostgreSQL 集成
- Redis 缓存客户端
- Alembic 数据库迁移
- Libvirt 集成框架
- SSH 自动化框架

## 📁 项目结构

```
backend/
├── app/
│   ├── api/v1/
│   │   ├── auth.py          # ✅ 认证接口
│   │   ├── users.py         # ✅ 用户管理
│   │   └── vms.py           # ✅ VM 管理
│   ├── core/
│   │   ├── config.py        # ✅ 配置管理
│   │   ├── security.py      # ✅ 安全工具
│   │   └── exceptions.py    # ✅ 异常处理
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── models.py    # ✅ 数据模型
│   │   │   └── base.py      # ✅ 数据库会话
│   │   ├── cache/
│   │   │   └── redis_client.py  # ✅ Redis 客户端
│   │   └── vm/
│   │       ├── libvirt_manager.py  # ✅ Libvirt 集成
│   │       └── ssh_client.py       # ✅ SSH 自动化
│   └── main.py              # ✅ FastAPI 应用
├── tests/
│   ├── conftest.py          # ✅ 测试配置
│   └── test_auth.py         # ✅ 认证测试
├── alembic/
│   └── versions/
│       └── 001_initial.py   # ✅ 初始迁移
├── requirements.txt         # ✅ 依赖列表
├── Dockerfile              # ✅ Docker 配置
└── README.md               # ✅ 文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入实际配置
```

### 3. 启动开发环境（Docker）

```bash
# 在项目根目录
docker-compose up -d postgres redis
```

### 4. 运行数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

### 5. 填充初始数据

```bash
python -m app.seed_data
```

### 6. 启动开发服务器

```bash
uvicorn app.main:app --reload
```

访问：
- API: http://localhost:8000
- 文档: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 📝 API 文档

### 认证接口

```http
# 注册
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "username": "johndoe"
}

# 登录
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded
username=user@example.com&password=SecurePass123!

# 刷新 Token
POST /api/v1/auth/refresh
{
  "refresh_token": "..."
}
```

### 用户接口

```http
# 获取当前用户
GET /api/v1/users/me
Authorization: Bearer {token}

# 更新用户信息
PATCH /api/v1/users/me
Authorization: Bearer {token}
{
  "username": "newname"
}

# 充值
POST /api/v1/users/me/recharge
Authorization: Bearer {token}
{
  "amount": 100.00,
  "payment_method": "alipay"
}
```

### VM 接口

```http
# 获取套餐列表
GET /api/v1/vms/plans

# 创建 VM
POST /api/v1/vms
Authorization: Bearer {token}
{
  "name": "my-vm",
  "plan_id": "uuid"
}

# 获取 VM 列表
GET /api/v1/vms?page=1&page_size=20
Authorization: Bearer {token}

# 获取 VM 详情
GET /api/v1/vms/{vm_id}
Authorization: Bearer {token}

# 启动 VM
POST /api/v1/vms/{vm_id}/start
Authorization: Bearer {token}

# 停止 VM
POST /api/v1/vms/{vm_id}/stop
Authorization: Bearer {token}

# 删除 VM
DELETE /api/v1/vms/{vm_id}
Authorization: Bearer {token}

# 续费 VM
POST /api/v1/vms/{vm_id}/renew
Authorization: Bearer {token}
{
  "months": 1
}
```

## 🧪 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_auth.py

# 生成覆盖率报告
pytest --cov=app tests/
```

## 🔧 开发工具

```bash
# 代码格式化
black app/

# 代码检查
flake8 app/

# 类型检查
mypy app/
```

## 🐳 Docker 部署

```bash
# 构建镜像
docker build -t openclaw-backend ./backend

# 运行容器
docker run -p 8000:8000 openclaw-backend
```

## 📋 待实现功能（P1）

- [ ] Agent 管理 API
- [ ] Channel 配置 API
- [ ] 计费系统实现
- [ ] Token 使用统计
- [ ] 管理员 API
- [ ] Libvirt 实际集成
- [ ] SSH 自动化部署
- [ ] 监控数据采集
- [ ] 邮件通知
- [ ] 日志聚合

## 🔐 安全注意事项

1. **生产环境必须修改**：
   - `JWT_SECRET_KEY`
   - `ENCRYPTION_KEY`
   - 数据库密码
   - Redis 密码

2. **HTTPS**：生产环境必须使用 HTTPS

3. **CORS**：配置正确的允许域名

4. **限流**：实现 API 限流保护

5. **日志**：不要记录敏感信息

## 📊 数据库架构

完整的数据库模型包括：

1. **users** - 用户表
2. **plans** - 套餐表
3. **vms** - 虚拟机表
4. **agent_templates** - Agent 模板表
5. **agents** - Agent 表
6. **channels** - 渠道表
7. **token_usage** - Token 使用记录表
8. **orders** - 订单表
9. **models** - 模型配置表
10. **system_configs** - 系统配置表

## 📞 联系方式

- 开发者: Coder Agent
- 项目: OpenClaw VM Platform
- 版本: 0.1.0-alpha

---

**状态**: ✅ P0 功能已完成，可进行集成测试
