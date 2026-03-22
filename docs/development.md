# OpenClaw VM Platform - 开发文档

## 目录

- [项目概述](#项目概述)
- [项目结构](#项目结构)
- [技术栈](#技术栈)
- [开发环境搭建](#开发环境搭建)
- [代码规范](#代码规范)
- [测试指南](#测试指南)
- [API 开发](#api-开发)
- [前端开发](#前端开发)
- [数据库管理](#数据库管理)
- [如何贡献](#如何贡献)

---

## 项目概述

OpenClaw VM Platform 是一个虚拟机租赁平台，让用户快速拥有自己的 OpenClaw 实例。

### 核心功能

- 用户认证与管理
- 虚拟机生命周期管理
- KVM/Libvirt 虚拟化集成
- 计费与订单系统
- 实时监控面板

### 架构设计

```
┌─────────────────────────────────────────┐
│        Frontend (React + TypeScript)    │
│              - Vite                      │
│              - React Router              │
│              - Tailwind CSS              │
└─────────────────────────────────────────┘
                    ↓ HTTP/REST
┌─────────────────────────────────────────┐
│        Backend (FastAPI + Python)        │
│              - JWT 认证                  │
│              - SQLAlchemy ORM            │
│              - Pydantic 验证             │
└─────────────────────────────────────────┘
          ↓                ↓
┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Redis     │
│  (持久化)    │  │   (缓存)     │
└──────────────┘  └──────────────┘
          ↓
┌─────────────────────────────────────────┐
│       Libvirt + KVM (虚拟化)             │
│              - QEMU                      │
│              - 存储池                    │
│              - 网络管理                  │
└─────────────────────────────────────────┘
```

---

## 项目结构

```
openclaw-vm-platform/
├── backend/                    # 后端代码
│   ├── alembic/               # 数据库迁移
│   │   ├── versions/          # 迁移文件
│   │   └── env.py             # 迁移环境配置
│   ├── app/                   # 应用主代码
│   │   ├── api/               # API 路由
│   │   │   ├── v1/            # v1 版本 API
│   │   │   │   ├── auth.py    # 认证接口
│   │   │   │   ├── users.py   # 用户接口
│   │   │   │   └── vms.py     # 虚拟机接口
│   │   │   └── deps.py        # 依赖注入
│   │   ├── core/              # 核心模块
│   │   │   ├── config.py      # 配置管理
│   │   │   ├── security.py    # 安全工具
│   │   │   ├── exceptions.py  # 异常定义
│   │   │   └── response.py    # 响应格式
│   │   ├── domain/            # 业务逻辑
│   │   ├── infrastructure/    # 基础设施
│   │   │   ├── database/      # 数据库
│   │   │   │   ├── base.py    # 基础类
│   │   │   │   └── models.py  # 数据模型
│   │   │   ├── cache/         # 缓存
│   │   │   │   └── redis_client.py
│   │   │   └── vm/            # 虚拟化
│   │   │       ├── libvirt_manager.py
│   │   │       └── ssh_client.py
│   │   ├── repositories/      # 数据仓库
│   │   ├── services/          # 业务服务
│   │   ├── main.py            # 应用入口
│   │   └── seed_data.py       # 种子数据
│   ├── tests/                 # 测试代码
│   │   ├── unit/              # 单元测试
│   │   └── integration/       # 集成测试
│   ├── scripts/               # 脚本
│   ├── requirements.txt       # 依赖列表
│   ├── Dockerfile             # Docker 构建文件
│   └── .env.example           # 环境变量示例
│
├── frontend/                   # 前端代码
│   ├── src/                   # 源代码
│   │   ├── api/               # API 客户端
│   │   ├── assets/            # 静态资源
│   │   ├── components/        # 组件
│   │   ├── hooks/             # 自定义 Hooks
│   │   ├── lib/               # 工具库
│   │   ├── pages/             # 页面
│   │   ├── types/             # TypeScript 类型
│   │   ├── main.tsx           # 入口文件
│   │   └── App.tsx            # 根组件
│   ├── public/                # 公共资源
│   ├── package.json           # 依赖配置
│   ├── tsconfig.json          # TypeScript 配置
│   ├── vite.config.ts         # Vite 配置
│   └── tailwind.config.js     # Tailwind 配置
│
├── docs/                       # 文档
│   ├── api.md                 # API 文档
│   ├── deployment.md          # 部署文档
│   ├── user-guide.md          # 用户手册
│   └── development.md         # 开发文档
│
├── scripts/                    # 工具脚本
├── docker-compose.yml          # Docker 编排
├── README.md                   # 项目说明
└── .gitignore                  # Git 忽略配置
```

---

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 编程语言 |
| FastAPI | 0.104+ | Web 框架 |
| SQLAlchemy | 2.0+ | ORM |
| Alembic | 1.12+ | 数据库迁移 |
| Pydantic | 2.0+ | 数据验证 |
| asyncpg | 0.29+ | 异步 PostgreSQL 驱动 |
| redis | 5.0+ | Redis 客户端 |
| libvirt-python | 9.0+ | Libvirt 绑定 |
| PyJWT | 2.8+ | JWT 处理 |
| passlib | 1.7+ | 密码哈希 |
| pytest | 7.4+ | 测试框架 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18+ | UI 框架 |
| TypeScript | 5.0+ | 类型安全 |
| Vite | 8.0+ | 构建工具 |
| React Router | 7.0+ | 路由 |
| Axios | 1.13+ | HTTP 客户端 |
| Tailwind CSS | 4.0+ | 样式框架 |

### 数据库 & 缓存

- **PostgreSQL**: 15+ - 主数据库
- **Redis**: 7+ - 缓存与会话

### 虚拟化

- **KVM**: 硬件虚拟化
- **Libvirt**: 虚拟化管理 API
- **QEMU**: 虚拟机模拟器

---

## 开发环境搭建

### 前置要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Libvirt 9.0+ (可选，用于虚拟机功能)

### 后端环境

#### 1. 克隆项目

```bash
git clone https://github.com/your-org/openclaw-vm-platform.git
cd openclaw-vm-platform/backend
```

#### 2. 创建虚拟环境

```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
```

#### 3. 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. 配置环境变量

```bash
cp .env.example .env
nano .env
```

最小配置:

```bash
DATABASE_URL=postgresql+asyncpg://openclaw:password@localhost:5432/openclaw
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=dev-secret-key-change-in-production
ENCRYPTION_KEY=dev-encryption-key-32-bytes
DEBUG=true
```

#### 5. 初始化数据库

```bash
# 创建数据库
createdb -U postgres openclaw

# 运行迁移
alembic upgrade head

# 加载种子数据
python -m app.seed_data
```

#### 6. 启动开发服务器

```bash
uvicorn app.main:app --reload --port 8000
```

访问:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

### 前端环境

#### 1. 安装依赖

```bash
cd ../frontend
npm install
```

#### 2. 配置环境变量

创建 `.env.development`:

```bash
VITE_API_URL=http://localhost:8000
```

#### 3. 启动开发服务器

```bash
npm run dev
```

访问: http://localhost:5173

### Docker 环境（推荐）

#### 1. 启动所有服务

```bash
cd ..  # 回到项目根目录
docker-compose up -d
```

#### 2. 查看日志

```bash
docker-compose logs -f
```

#### 3. 进入容器

```bash
# 后端
docker-compose exec backend bash

# 数据库
docker-compose exec postgres psql -U openclaw -d openclaw
```

---

## 代码规范

### Python 代码规范

遵循 **PEP 8** 和 **Google Python Style Guide**。

#### 格式化工具

使用以下工具自动格式化:

```bash
# 安装工具
pip install black isort flake8 mypy

# 格式化代码
black app/
isort app/

# 检查代码质量
flake8 app/
mypy app/
```

#### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `UserManager` |
| 函数名 | snake_case | `create_user()` |
| 变量名 | snake_case | `user_name` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| 私有属性 | _前缀 | `_internal_data` |

#### 文档字符串

```python
def create_vm(name: str, plan_id: str) -> VM:
    """
    Create a new virtual machine.
    
    Args:
        name: VM name (3-100 characters)
        plan_id: Plan ID to use
        
    Returns:
        Created VM instance
        
    Raises:
        NotFoundError: If plan not found
        InsufficientBalanceError: If user balance is insufficient
        
    Example:
        >>> vm = create_vm("my-vm", "plan-basic")
        >>> print(vm.name)
        my-vm
    """
    pass
```

#### 类型注解

```python
from typing import List, Optional, Dict, Any

# 函数参数和返回值
async def get_users(
    skip: int = 0,
    limit: int = 20,
    status_filter: Optional[str] = None
) -> List[User]:
    pass

# 变量注解
user_count: int = 0
user_list: List[User] = []
config: Dict[str, Any] = {}
```

#### 异步代码

```python
# 使用 async/await
async def fetch_user(user_id: str) -> User:
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one()

# 并发执行
async def fetch_all():
    users, plans = await asyncio.gather(
        fetch_users(),
        fetch_plans()
    )
    return users, plans
```

### TypeScript 代码规范

遵循 **Airbnb JavaScript Style Guide**。

#### 格式化工具

```bash
# 安装工具
npm install --save-dev prettier eslint

# 格式化代码
npm run lint
npm run format
```

#### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件名 | PascalCase | `UserCard` |
| 函数名 | camelCase | `fetchUsers()` |
| 变量名 | camelCase | `userName` |
| 常量 | UPPER_SNAKE_CASE | `API_BASE_URL` |
| 接口/类型 | PascalCase | `User` |

#### 组件结构

```typescript
// 导入
import React, { useState, useEffect } from 'react';
import { User } from '../types';

// 类型定义
interface UserCardProps {
  user: User;
  onUpdate: (user: User) => void;
}

// 组件
export const UserCard: React.FC<UserCardProps> = ({ user, onUpdate }) => {
  // State
  const [isEditing, setIsEditing] = useState(false);

  // Effects
  useEffect(() => {
    // 初始化逻辑
  }, []);

  // Handlers
  const handleUpdate = () => {
    onUpdate(user);
  };

  // Render
  return (
    <div className="user-card">
      {/* 组件内容 */}
    </div>
  );
};
```

#### API 调用

```typescript
// 使用 axios
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 添加认证拦截器
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// API 函数
export const fetchUsers = async (): Promise<User[]> => {
  const response = await api.get('/api/v1/users');
  return response.data.data;
};
```

---

## 测试指南

### 后端测试

#### 测试结构

```
tests/
├── unit/              # 单元测试
│   ├── test_security.py
│   └── test_utils.py
├── integration/       # 集成测试
│   ├── test_auth.py
│   ├── test_vms.py
│   └── test_users.py
└── conftest.py        # 测试配置
```

#### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_security.py

# 运行带覆盖率
pytest --cov=app --cov-report=html

# 运行标记的测试
pytest -m "not slow"
```

#### 测试示例

**单元测试**:

```python
# tests/unit/test_security.py
from app.core.security import hash_password, verify_password

def test_hash_password():
    """Test password hashing."""
    password = "securepassword123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)
```

**集成测试**:

```python
# tests/integration/test_auth.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_register_user(client):
    """Test user registration."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "securepassword123",
            "username": "testuser"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "test@example.com"
```

**异步测试**:

```python
# tests/integration/test_vms.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_vm():
    """Test VM creation."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 先登录获取 token
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "password"}
        )
        token = login_response.json()["data"]["access_token"]
        
        # 创建 VM
        response = await client.post(
            "/api/v1/vms",
            json={"name": "test-vm", "plan_id": "plan-basic"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
```

### 前端测试

#### 安装测试工具

```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom vitest
```

#### 测试示例

```typescript
// src/components/__tests__/UserCard.test.tsx
import { render, screen } from '@testing-library/react';
import { UserCard } from '../UserCard';

describe('UserCard', () => {
  it('should render user information', () => {
    const user = {
      id: '1',
      name: 'Test User',
      email: 'test@example.com',
    };

    render(<UserCard user={user} />);

    expect(screen.getByText('Test User')).toBeInTheDocument();
    expect(screen.getByText('test@example.com')).toBeInTheDocument();
  });
});
```

#### 运行测试

```bash
# 运行测试
npm test

# 运行监听模式
npm test -- --watch

# 运行覆盖率
npm test -- --coverage
```

---

## API 开发

### 创建新端点

#### 1. 定义请求/响应模型

```python
# app/api/v1/vms.py
from pydantic import BaseModel, Field

class VMCreateRequest(BaseModel):
    """VM creation request."""
    name: str = Field(..., min_length=3, max_length=100)
    plan_id: str
    region: Optional[str] = "default"

class VMResponse(BaseModel):
    """VM response model."""
    id: str
    name: str
    status: str
    ip_address: Optional[str]
    
    class Config:
        from_attributes = True
```

#### 2. 实现路由处理

```python
from fastapi import APIRouter, Depends
from app.infrastructure.database.base import get_db
from app.api.deps import get_current_active_user

router = APIRouter()

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_vm(
    request: VMCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new virtual machine.
    
    Args:
        request: VM creation request
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created VM information
    """
    # 业务逻辑
    vm = await vm_service.create(request, current_user, db)
    
    return success_response(
        VMResponse.from_orm(vm).dict(),
        "VM created successfully"
    )
```

#### 3. 注册路由

```python
# app/main.py
from app.api.v1 import vms

app.include_router(
    vms.router,
    prefix=f"{settings.API_V1_PREFIX}/vms",
    tags=["虚拟机"]
)
```

### 依赖注入

#### 认证依赖

```python
# app/api/deps.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user
```

#### 分页依赖

```python
def get_pagination_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
) -> tuple[int, int]:
    """Get pagination parameters."""
    skip = (page - 1) * page_size
    return skip, page_size
```

### 错误处理

#### 自定义异常

```python
# app/core/exceptions.py
class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code

class NotFoundError(AppException):
    """Resource not found exception."""
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            code="NOT_FOUND_ERROR"
        )
```

#### 全局异常处理器

```python
# app/core/exceptions.py
from fastapi import Request
from fastapi.responses import JSONResponse

def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message
                }
            }
        )
```

---

## 前端开发

### 组件开发

#### 创建新页面

```typescript
// src/pages/VMDashboard.tsx
import React, { useEffect, useState } from 'react';
import { fetchVMs } from '../api/vms';
import { VM } from '../types';

export const VMDashboard: React.FC = () => {
  const [vms, setVMs] = useState<VM[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadVMs();
  }, []);

  const loadVMs = async () => {
    try {
      const data = await fetchVMs();
      setVMs(data);
    } catch (error) {
      console.error('Failed to load VMs:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="vm-dashboard">
      <h1>Virtual Machines</h1>
      <div className="vm-list">
        {vms.map(vm => (
          <VMCard key={vm.id} vm={vm} />
        ))}
      </div>
    </div>
  );
};
```

#### 添加路由

```typescript
// src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { VMDashboard } from './pages/VMDashboard';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/vms" element={<VMDashboard />} />
        {/* 其他路由 */}
      </Routes>
    </BrowserRouter>
  );
}
```

### 状态管理

使用 React Context 或状态管理库:

```typescript
// src/contexts/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react';

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const login = async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password });
    const { access_token, user } = response.data.data;
    
    setToken(access_token);
    setUser(user);
    localStorage.setItem('token', access_token);
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

---

## 数据库管理

### 数据库迁移

#### 创建迁移

```bash
# 自动生成迁移（检测模型变化）
alembic revision --autogenerate -m "Add user balance field"

# 手动创建迁移
alembic revision -m "Custom migration"
```

#### 执行迁移

```bash
# 升级到最新版本
alembic upgrade head

# 升级到特定版本
alembic upgrade <revision_id>

# 回滚一个版本
alembic downgrade -1

# 回滚到特定版本
alembic downgrade <revision_id>

# 查看当前版本
alembic current

# 查看历史
alembic history
```

#### 迁移示例

```python
# alembic/versions/xxxx_add_user_balance.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('balance', sa.Numeric(10, 2), nullable=False, server_default='0'))

def downgrade():
    op.drop_column('users', 'balance')
```

### 数据模型

#### 定义模型

```python
# app/infrastructure/database/models.py
from sqlalchemy import Column, String, Integer, DateTime, Enum, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.infrastructure.database.base import Base
import uuid
import enum

class VMStatus(str, enum.Enum):
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

class VM(Base):
    __tablename__ = "vms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    status = Column(Enum(VMStatus), default=VMStatus.CREATING)
    ip_address = Column(String(50), nullable=True)
    cpu = Column(Integer, nullable=False)
    memory = Column(Integer, nullable=False)
    disk = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
```

---

## 如何贡献

### 贡献流程

1. **Fork 项目**
   ```bash
   # 在 GitHub 上 Fork 项目
   git clone https://github.com/your-username/openclaw-vm-platform.git
   cd openclaw-vm-platform
   ```

2. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **编写代码**
   - 遵循代码规范
   - 添加单元测试
   - 更新相关文档

4. **运行测试**
   ```bash
   # 后端
   pytest
   
   # 前端
   npm test
   ```

5. **提交代码**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   **Commit 消息规范**:
   - `feat`: 新功能
   - `fix`: 修复 bug
   - `docs`: 文档更新
   - `style`: 代码格式调整
   - `refactor`: 代码重构
   - `test`: 测试相关
   - `chore`: 构建/工具相关

6. **推送分支**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写 PR 模板
   - 等待代码审查

### 代码审查清单

提交 PR 前请确保:

- [ ] 代码遵循项目规范
- [ ] 所有测试通过
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] 没有引入安全漏洞
- [ ] 性能没有明显下降
- [ ] Commit 消息清晰明了

### 报告 Bug

如发现 Bug，请创建 Issue 并包含:

1. **Bug 描述**: 清晰描述问题
2. **复现步骤**: 如何重现该问题
3. **期望行为**: 应该发生什么
4. **实际行为**: 实际发生了什么
5. **环境信息**: OS、Python 版本、Node 版本等
6. **日志/截图**: 相关的错误信息

### 功能建议

欢迎提出新功能建议！请在 Issue 中说明:

1. **功能描述**: 详细描述该功能
2. **使用场景**: 为什么需要这个功能
3. **实现建议**: 可选的实现思路
4. **替代方案**: 是否有其他解决方案

---

## 开发资源

### 文档

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [React 文档](https://react.dev/)
- [TypeScript 文档](https://www.typescriptlang.org/docs/)
- [Libvirt 文档](https://libvirt.org/docs.html)

### 工具

- **PyCharm** / **VS Code**: 推荐的 IDE
- **Postman**: API 测试工具
- **DBeaver**: 数据库管理工具
- **Redis Desktop Manager**: Redis 管理工具

### 社区

- **GitHub Discussions**: 讨论和问答
- **Discord**: 实时交流（链接待添加）
- **邮件列表**: dev@openclaw.example.com

---

_最后更新: 2026-03-22_
_文档版本: 1.0.0_
