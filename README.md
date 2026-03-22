# OpenClaw VM Platform

OpenClaw 虚拟机租赁平台 - 让用户轻松拥有自己的 OpenClaw 实例

## 功能特性

- ✅ 一键创建 OpenClaw 虚拟机
- ✅ 多种套餐选择
- ✅ 自动化部署和配置
- ✅ Telegram/WhatsApp 渠道配置向导
- ✅ 实时监控和管理
- ✅ 灵活的计费系统

## 快速开始

### 环境要求

- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### 安装

```bash
# 克隆项目
git clone https://github.com/your-org/openclaw-vm-platform.git
cd openclaw-vm-platform

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入实际配置

# 初始化数据库
psql -U postgres -f scripts/init-db.sql

# 启动开发服务器
npm run dev
```

### 生产部署

```bash
# 构建
npm run build

# 启动
npm start
```

## API 文档

### 认证

```
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

### VM 管理

```
POST   /api/vm/create      - 创建 VM
GET    /api/vm/list        - 获取 VM 列表
GET    /api/vm/:vmId       - 获取 VM 详情
POST   /api/vm/:vmId/start - 启动 VM
POST   /api/vm/:vmId/stop  - 停止 VM
DELETE /api/vm/:vmId       - 删除 VM
```

### 渠道配置

```
POST   /api/channel/telegram      - 配置 Telegram
GET    /api/channel/:vmId         - 获取渠道列表
DELETE /api/channel/:vmId/:type   - 删除渠道
```

## 架构

```
┌─────────────────────────────────────────┐
│           用户门户 (Web UI)              │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│           API Gateway (Express)          │
└─────────────────────────────────────────┘
                    ↓
┌──────────────┬──────────────┬───────────┐
│  VM Service  │Channel Svc   │ Billing   │
└──────────────┴──────────────┴───────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Cloud Provider (Aliyun)         │
│         - KVM / OpenStack               │
│         - 预装 OpenClaw 镜像             │
└─────────────────────────────────────────┘
```

## 开发路线

### Phase 1 (当前)
- [x] 基础架构
- [ ] 用户系统
- [ ] VM 管理（手动创建）
- [ ] Telegram 配置向导

### Phase 2
- [ ] 自动化 VM 创建
- [ ] 计费系统
- [ ] 监控面板

### Phase 3
- [ ] Agent 市场
- [ ] AI 运维助手
- [ ] 企业版功能

## 许可证

MIT
