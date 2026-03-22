# OpenClaw VM Platform - 部署文档

## 目录

- [环境要求](#环境要求)
- [快速部署（Docker）](#快速部署docker)
- [手动部署](#手动部署)
- [配置说明](#配置说明)
- [生产环境部署](#生产环境部署)
- [监控与日志](#监控与日志)
- [故障排查](#故障排查)

---

## 环境要求

### 硬件要求

#### 最低配置
- CPU: 2核
- 内存: 4GB
- 磁盘: 40GB

#### 推荐配置
- CPU: 4核+
- 内存: 8GB+
- 磁盘: 100GB+ SSD

### 软件要求

#### 后端
- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Redis**: 7+
- **Libvirt**: 9.0+ (虚拟化管理)
- **QEMU/KVM**: 支持硬件虚拟化

#### 前端
- **Node.js**: 18+ (推荐 20+)
- **npm** 或 **yarn**

#### 可选
- **Docker**: 24.0+
- **Docker Compose**: 2.20+

### 系统要求
- **操作系统**: Ubuntu 22.04+ / CentOS 8+ / Debian 11+
- **架构**: x86_64 (amd64)
- **权限**: root 或 sudo 权限（用于 Libvirt）

---

## 快速部署（Docker）

### 1. 克隆项目

```bash
git clone https://github.com/your-org/openclaw-vm-platform.git
cd openclaw-vm-platform
```

### 2. 配置环境变量

```bash
# 复制示例配置
cp backend/.env.example backend/.env

# 编辑配置文件
nano backend/.env
```

**必须修改的配置项**：

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://openclaw:your_secure_password@postgres:5432/openclaw

# Redis
REDIS_URL=redis://redis:6379/0

# JWT 密钥（使用强随机字符串）
JWT_SECRET_KEY=$(openssl rand -hex 32)

# 加密密钥（32字节）
ENCRYPTION_KEY=$(openssl rand -hex 16)

# 生产环境
DEBUG=false
```

### 3. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps
```

### 4. 初始化数据库

```bash
# 进入后端容器
docker-compose exec backend bash

# 运行数据库迁移
alembic upgrade head

# 初始化种子数据（套餐、管理员等）
python -m app.seed_data

# 退出容器
exit
```

### 5. 验证部署

```bash
# 检查后端健康状态
curl http://localhost:8000/health

# 访问 API 文档
open http://localhost:8000/api/docs

# 前端访问（如果已构建）
open http://localhost:3000
```

---

## 手动部署

### 后端部署

#### 1. 安装系统依赖

**Ubuntu/Debian**:

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
    postgresql-15 redis-server libvirt-dev qemu-kvm
```

**CentOS/RHEL**:

```bash
sudo yum install -y python3.11 python3.11-pip \
    postgresql15-server redis libvirt-devel qemu-kvm
```

#### 2. 配置 PostgreSQL

```bash
# 启动 PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql
```

```sql
CREATE USER openclaw WITH PASSWORD 'your_secure_password';
CREATE DATABASE openclaw OWNER openclaw;
GRANT ALL PRIVILEGES ON DATABASE openclaw TO openclaw;
\q
```

#### 3. 配置 Redis

```bash
# 启动 Redis
sudo systemctl start redis
sudo systemctl enable redis

# 测试连接
redis-cli ping
```

#### 4. 配置 Libvirt

```bash
# 启动 Libvirt
sudo systemctl start libvirtd
sudo systemctl enable libvirtd

# 将当前用户添加到 libvirt 组
sudo usermod -aG libvirt $USER

# 配置存储池和网络
sudo virsh pool-define-as --name openclaw-vms --type dir --target /var/lib/libvirt/openclaw
sudo virsh pool-build openclaw-vms
sudo virsh pool-start openclaw-vms
sudo virsh pool-autostart openclaw-vms
```

#### 5. 安装 Python 依赖

```bash
cd backend

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

#### 6. 配置环境变量

```bash
# 创建 .env 文件
cat > .env << EOF
# 应用配置
APP_NAME=OpenClaw VM Platform
APP_VERSION=1.0.0
DEBUG=false
API_V1_PREFIX=/api/v1

# 数据库
DATABASE_URL=postgresql+asyncpg://openclaw:your_secure_password@localhost:5432/openclaw
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# JWT
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Libvirt
LIBVIRT_URI=qemu:///system
LIBVIRT_POOL_NAME=openclaw-vms
LIBVIRT_NETWORK_NAME=default

# SSH
SSH_PRIVATE_KEY_PATH=/root/.ssh/id_rsa
SSH_USER=root

# VM 配置
VM_BASE_IMAGE_PATH=/var/lib/libvirt/images/base.qcow2
VM_DEFAULT_CPU=1
VM_DEFAULT_MEMORY=2048
VM_DEFAULT_DISK=20

# 计费
TOKEN_PRICE_PER_1K=0.01
DISK_PRICE_PER_GB=0.5
BACKUP_PRICE_PER_MONTH=20.0

# CORS
CORS_ORIGINS=["https://yourdomain.com"]

# 加密
ENCRYPTION_KEY=$(openssl rand -hex 16)
EOF
```

#### 7. 初始化数据库

```bash
# 运行迁移
alembic upgrade head

# 加载种子数据
python -m app.seed_data
```

#### 8. 启动后端服务

**开发模式**:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**生产模式（使用 Gunicorn）**:

```bash
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
```

**Systemd 服务**:

创建服务文件 `/etc/systemd/system/openclaw-backend.service`:

```ini
[Unit]
Description=OpenClaw VM Platform Backend
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=openclaw
Group=openclaw
WorkingDirectory=/opt/openclaw-vm-platform/backend
Environment="PATH=/opt/openclaw-vm-platform/backend/venv/bin"
ExecStart=/opt/openclaw-vm-platform/backend/venv/bin/gunicorn \
    app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /var/log/openclaw/access.log \
    --error-logfile /var/log/openclaw/error.log
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务:

```bash
sudo systemctl daemon-reload
sudo systemctl start openclaw-backend
sudo systemctl enable openclaw-backend
sudo systemctl status openclaw-backend
```

### 前端部署

#### 1. 安装依赖

```bash
cd frontend
npm install
```

#### 2. 配置环境变量

创建 `.env.production`:

```bash
VITE_API_URL=https://api.yourdomain.com
VITE_APP_NAME=OpenClaw VM Platform
```

#### 3. 构建生产版本

```bash
npm run build
```

构建产物位于 `dist/` 目录。

#### 4. 部署静态文件

**使用 Nginx**:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    root /var/www/openclaw-frontend/dist;
    index index.html;

    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 支持（未来）
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 静态文件缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

启用配置:

```bash
sudo ln -s /etc/nginx/sites-available/openclaw /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 配置说明

### 环境变量详解

#### 应用配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| APP_NAME | string | OpenClaw VM Platform | 应用名称 |
| APP_VERSION | string | 1.0.0 | 应用版本 |
| DEBUG | boolean | false | 调试模式（生产环境必须为 false） |
| API_V1_PREFIX | string | /api/v1 | API 路径前缀 |

#### 数据库配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| DATABASE_URL | string | - | PostgreSQL 连接字符串 |
| DB_POOL_SIZE | int | 20 | 连接池大小 |
| DB_MAX_OVERFLOW | int | 10 | 最大溢出连接数 |

#### Redis 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| REDIS_URL | string | - | Redis 连接字符串 |
| REDIS_MAX_CONNECTIONS | int | 50 | 最大连接数 |

#### JWT 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| JWT_SECRET_KEY | string | - | JWT 签名密钥（必须设置） |
| JWT_ALGORITHM | string | HS256 | 加密算法 |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | int | 30 | Access Token 过期时间（分钟） |
| JWT_REFRESH_TOKEN_EXPIRE_DAYS | int | 7 | Refresh Token 过期时间（天） |

#### Libvirt 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| LIBVIRT_URI | string | qemu:///system | Libvirt 连接 URI |
| LIBVIRT_POOL_NAME | string | openclaw-vms | 存储池名称 |
| LIBVIRT_NETWORK_NAME | string | openclaw-network | 网络名称 |

#### VM 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| VM_BASE_IMAGE_PATH | string | /var/lib/libvirt/images/base.qcow2 | 基础镜像路径 |
| VM_DEFAULT_CPU | int | 1 | 默认 CPU 核数 |
| VM_DEFAULT_MEMORY | int | 2048 | 默认内存（MB） |
| VM_DEFAULT_DISK | int | 20 | 默认磁盘（GB） |

### 安全配置建议

#### 1. 生成强密钥

```bash
# JWT 密钥（64字节）
openssl rand -hex 32

# 加密密钥（32字节）
openssl rand -hex 16
```

#### 2. 数据库安全

```sql
-- 限制连接来源
-- 编辑 pg_hba.conf，只允许特定 IP 连接

-- 使用强密码
ALTER USER openclaw WITH PASSWORD 'complex_password_here';

-- 限制权限
REALL ALL PRIVILEGES ON DATABASE openclaw FROM PUBLIC;
GRANT CONNECT ON DATABASE openclaw TO openclaw;
```

#### 3. Redis 安全

编辑 `/etc/redis/redis.conf`:

```conf
# 绑定本地地址
bind 127.0.0.1

# 设置密码
requirepass your_redis_password

# 禁用危险命令
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
```

#### 4. 防火墙配置

```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable

# Firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --reload
```

---

## 生产环境部署

### SSL/TLS 配置

使用 Let's Encrypt 免费证书:

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 自动续期
sudo systemctl enable certbot.timer
```

### 性能优化

#### 后端优化

```bash
# Gunicorn 配置
gunicorn app.main:app \
    --workers $(nproc) \
    --worker-class uvicorn.workers.UvicornWorker \
    --threads 4 \
    --worker-connections 1000 \
    --max-requests 10000 \
    --max-requests-jitter 1000 \
    --timeout 120 \
    --keep-alive 5
```

#### PostgreSQL 优化

编辑 `/etc/postgresql/15/main/postgresql.conf`:

```conf
# 内存配置
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
work_mem = 4MB

# 连接配置
max_connections = 100

# WAL 配置
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

#### Redis 优化

编辑 `/etc/redis/redis.conf`:

```conf
# 内存配置
maxmemory 2gb
maxmemory-policy allkeys-lru

# 持久化
save 900 1
save 300 10
save 60 10000
```

#### Nginx 优化

```nginx
# 全局配置
worker_processes auto;
worker_connections 2048;

# HTTP 配置
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript;

# 连接优化
keepalive_timeout 65;
client_max_body_size 20M;
```

### 备份策略

#### 数据库备份

```bash
#!/bin/bash
# backup-db.sh

BACKUP_DIR="/var/backups/openclaw"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份 PostgreSQL
pg_dump -U openclaw openclaw | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# 保留最近7天的备份
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_$DATE.sql.gz"
```

设置定时任务:

```bash
# crontab -e
0 2 * * * /opt/openclaw/scripts/backup-db.sh >> /var/log/openclaw/backup.log 2>&1
```

---

## 监控与日志

### 应用日志

**后端日志位置**:
- 访问日志: `/var/log/openclaw/access.log`
- 错误日志: `/var/log/openclaw/error.log`

**查看日志**:

```bash
# 实时查看
tail -f /var/log/openclaw/error.log

# Docker 环境
docker-compose logs -f backend
```

### 系统监控

#### Prometheus + Grafana（推荐）

1. 安装 Prometheus:

```bash
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v /opt/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

2. 配置指标导出（在 FastAPI 中集成 `prometheus-fastapi-instrumentator`）

3. Grafana 仪表板导入

#### 简单监控脚本

```bash
#!/bin/bash
# health-check.sh

# 检查后端
curl -f http://localhost:8000/health || echo "Backend is down!"

# 检查数据库
pg_isready -U openclaw -d openclaw || echo "Database is down!"

# 检查 Redis
redis-cli ping || echo "Redis is down!"

# 检查 Libvirt
virsh list || echo "Libvirt is down!"
```

---

## 故障排查

### 常见问题

#### 1. 后端无法启动

**症状**: `ModuleNotFoundError` 或数据库连接失败

**解决方案**:

```bash
# 检查虚拟环境
source venv/bin/activate
pip list

# 检查数据库连接
psql -U openclaw -d openclaw -h localhost

# 检查环境变量
env | grep DATABASE_URL
```

#### 2. Libvirt 权限错误

**症状**: `Permission denied` 或 `Failed to connect to hypervisor`

**解决方案**:

```bash
# 检查用户组
groups $USER

# 添加到 libvirt 组
sudo usermod -aG libvirt $USER
# 重新登录

# 检查 Libvirt 状态
sudo systemctl status libvirtd
virsh list
```

#### 3. VM 创建失败

**症状**: VM 状态一直为 `creating`

**解决方案**:

```bash
# 检查存储池
virsh pool-list --all
virsh pool-info openclaw-vms

# 检查网络
virsh net-list --all

# 查看日志
tail -f /var/log/libvirt/qemu/*.log
```

#### 4. 前端无法连接后端

**症状**: CORS 错误或网络超时

**解决方案**:

```bash
# 检查 CORS 配置
grep CORS_ORIGINS backend/.env

# 检查 Nginx 代理
sudo nginx -t
tail -f /var/log/nginx/error.log

# 测试 API
curl http://localhost:8000/health
```

#### 5. 数据库迁移失败

**症状**: `alembic upgrade head` 失败

**解决方案**:

```bash
# 检查迁移状态
alembic current
alembic history

# 回滚
alembic downgrade -1

# 重新迁移
alembic upgrade head

# 如果严重损坏，重新初始化
dropdb openclaw
createdb -O openclaw openclaw
alembic upgrade head
```

### 性能问题

#### CPU 占用过高

```bash
# 查看进程
top -p $(pgrep -d',' -f "gunicorn|uvicorn")

# 检查 VM 数量
virsh list --all

# 优化 Gunicorn workers
# 减少 worker 数量或使用异步 worker
```

#### 内存不足

```bash
# 检查内存使用
free -h
ps aux --sort=-%mem | head -10

# 调整 PostgreSQL
# 减少 shared_buffers

# 调整 Redis
# 设置 maxmemory
```

---

## 升级指南

### 后端升级

```bash
# 1. 备份数据库
pg_dump -U openclaw openclaw > backup_$(date +%Y%m%d).sql

# 2. 拉取新代码
git pull origin main

# 3. 更新依赖
source venv/bin/activate
pip install -r requirements.txt

# 4. 运行迁移
alembic upgrade head

# 5. 重启服务
sudo systemctl restart openclaw-backend
```

### 前端升级

```bash
# 1. 拉取新代码
git pull origin main

# 2. 更新依赖
npm install

# 3. 构建新版本
npm run build

# 4. 部署
sudo rm -rf /var/www/openclaw-frontend/dist
sudo cp -r dist /var/www/openclaw-frontend/

# 5. 清除浏览器缓存（用户端）
```

---

## 安全检查清单

- [ ] 修改所有默认密码（数据库、Redis、JWT密钥）
- [ ] 启用 HTTPS（SSL/TLS）
- [ ] 配置防火墙规则
- [ ] 禁用 DEBUG 模式
- [ ] 设置安全的 CORS 策略
- [ ] 配置日志轮转
- [ ] 设置自动备份
- [ ] 启用监控和告警
- [ ] 定期更新依赖包
- [ ] 配置 fail2ban（SSH 保护）

---

_最后更新: 2026-03-22_
_文档版本: 1.0.0_
