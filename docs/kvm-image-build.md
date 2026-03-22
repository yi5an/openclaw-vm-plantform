# KVM 镜像制作指南

## 前提条件

- 本地有 KVM 环境
- 有 libvirt、virt-install、qemu-img 工具
- 有 Ubuntu 22.04 ISO 或云镜像

## 镜像制作流程

### 1. 创建基础镜像

```bash
# 下载 Ubuntu 云镜像
wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img

# 创建工作镜像（20GB）
qemu-img create -f qcow2 -b jammy-server-cloudimg-amd64.img -F qcow2 openclaw-base.qcow2 20G
```

### 2. 启动临时 VM

```bash
# 创建 cloud-init 配置
cat > user-data.yaml <<EOF
#cloud-config
password: openclaw
chpasswd: { expire: False }
ssh_pwauth: True

packages:
  - nodejs
  - npm
  - docker.io
  - git
  - curl
  - wget

runcmd:
  - npm install -g openclaw
  - systemctl enable docker
  - systemctl start docker
EOF

# 启动 VM
virt-install \
  --name openclaw-base-builder \
  --memory 2048 \
  --vcpus 2 \
  --disk path=openclaw-base.qcow2,format=qcow2 \
  --cloud-init user-data=user-data.yaml \
  --network network=default \
  --graphics none \
  --import
```

### 3. SSH 配置

```bash
# 获取 VM IP
virsh domifaddr openclaw-base-builder

# SSH 连接（密码: openclaw）
ssh ubuntu@<VM_IP>
```

### 4. 安装 OpenClaw（在 VM 内）

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 安装 Docker
sudo apt install -y docker.io
sudo usermod -aG docker $USER

# 安装 OpenClaw
sudo npm install -g openclaw

# 初始化 OpenClaw
openclaw init

# 配置自启动
sudo tee /etc/systemd/system/openclaw-gateway.service <<EOF
[Unit]
Description=OpenClaw Gateway
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/usr/bin/openclaw gateway start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable openclaw-gateway
```

### 5. 清理并打包

```bash
# 退出 VM
exit

# 关闭 VM
virsh shutdown openclaw-base-builder

# 等待关闭
virsh destroy openclaw-base-builder  # 如果卡住

# 移除 VM 定义
virsh undefine openclaw-base-builder

# 压缩镜像
qemu-img convert -O qcow2 -c openclaw-base.qcow2 openclaw-base-compressed.qcow2
```

---

## 场景镜像

### 个人助手镜像

在基础镜像上添加：

```bash
# 启动基础镜像
virt-install \
  --name openclaw-personal-builder \
  --memory 2048 \
  --vcpus 2 \
  --disk path=openclaw-personal.qcow2,format=qcow2,backing_file=openclaw-base.qcow2 \
  --network network=default \
  --graphics none \
  --import

# SSH 连接
ssh ubuntu@<VM_IP>

# 创建个人助手 Agent
openclaw agent create personal-assistant \
  --name "个人助手" \
  --model zai/glm-5 \
  --prompt "你是一个贴心的个人助手..."

# 关闭并保存
```

### 数据分析镜像

```bash
# 创建数据分析 Agent
openclaw agent create data-analyst \
  --name "数据分析师" \
  --model deepseek/deepseek-reasoner \
  --prompt "你是一个专业的数据分析师..."

# 安装额外工具
sudo apt install -y python3-pip
pip3 install pandas numpy matplotlib
```

---

## 镜像管理脚本

### build-base.sh

```bash
#!/bin/bash
set -e

IMAGE_NAME="openclaw-base"
SIZE="20G"
UBUNTU_IMG="jammy-server-cloudimg-amd64.img"

echo "=== 下载 Ubuntu 云镜像 ==="
if [ ! -f "$UBUNTU_IMG" ]; then
  wget https://cloud-images.ubuntu.com/jammy/current/$UBUNTU_IMG
fi

echo "=== 创建工作镜像 ==="
qemu-img create -f qcow2 -b $UBUNTU_IMG -F qcow2 ${IMAGE_NAME}.qcow2 $SIZE

echo "=== 创建 cloud-init 配置 ==="
cat > user-data.yaml <<EOF
#cloud-config
password: openclaw
chpasswd: { expire: False }
ssh_pwauth: True
packages:
  - nodejs
  - npm
  - docker.io
  - git
EOF

cat > meta-data.yaml <<EOF
instance-id: openclaw-base
local-hostname: openclaw
EOF

echo "=== 启动 VM ==="
virt-install \
  --name ${IMAGE_NAME}-builder \
  --memory 2048 \
  --vcpus 2 \
  --disk path=${IMAGE_NAME}.qcow2,format=qcow2 \
  --cloud-init user-data=user-data.yaml,meta-data=meta-data.yaml \
  --network network=default \
  --graphics none \
  --import \
  --noautoconsole

echo "=== 等待 VM 启动 ==="
sleep 60

echo "=== 获取 IP ==="
IP=$(virsh domifaddr ${IMAGE_NAME}-builder | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
echo "VM IP: $IP"

echo "=== 下一步 ==="
echo "SSH 连接: ssh ubuntu@$IP (密码: openclaw)"
echo "然后运行: ./install-openclaw.sh"
```

### install-openclaw.sh

```bash
#!/bin/bash
set -e

echo "=== 更新系统 ==="
sudo apt update && sudo apt upgrade -y

echo "=== 安装 Node.js 20 ==="
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

echo "=== 安装 Docker ==="
sudo apt install -y docker.io
sudo usermod -aG docker $USER

echo "=== 安装 OpenClaw ==="
sudo npm install -g openclaw

echo "=== 初始化 OpenClaw ==="
openclaw init

echo "=== 配置 systemd 服务 ==="
sudo tee /etc/systemd/system/openclaw-gateway.service <<EOF
[Unit]
Description=OpenClaw Gateway
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/usr/bin/openclaw gateway start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable openclaw-gateway

echo "=== 完成 ==="
echo "请运行: sudo systemctl start openclaw-gateway"
```

---

## 镜像规格

| 镜像 | 大小 | 包含 |
|-----|------|------|
| openclaw-base.qcow2 | ~2GB | Ubuntu + Node.js + Docker + OpenClaw |
| openclaw-personal.qcow2 | ~2.5GB | base + 个人助手 Agent |
| openclaw-analyst.qcow2 | ~3GB | base + 数据分析 Agent + Python工具 |

---

## 注意事项

1. **网络配置**：镜像使用 DHCP，启动时会自动获取 IP
2. **SSH 访问**：用户名 `ubuntu`，密码 `openclaw`（首次登录后请修改）
3. **OpenClaw 配置**：需要用户自己配置 API Key 和渠道
4. **磁盘扩容**：qcow2 支持动态扩容，按需调整

---

*文档版本: v1.0*
*创建日期: 2026-03-04*
