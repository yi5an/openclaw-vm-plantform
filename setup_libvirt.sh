#!/bin/bash
# Libvirt 环境准备脚本
# 用途：配置 Libvirt 环境，确保 VM 创建功能正常工作

set -e

echo "========================================="
echo "Libvirt 环境准备脚本"
echo "========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
  echo -e "${YELLOW}提示：建议使用 sudo 运行此脚本${NC}"
fi

# 1. 检查 Libvirt 服务
echo -e "${YELLOW}[1/7] 检查 Libvirt 服务...${NC}"
if systemctl is-active --quiet libvirtd; then
  echo -e "${GREEN}✓ Libvirt 服务运行中${NC}"
else
  echo -e "${YELLOW}! Libvirt 服务未运行，正在启动...${NC}"
  sudo systemctl start libvirtd
  sudo systemctl enable libvirtd
fi

# 2. 创建 openclaw-vms 存储池
echo ""
echo -e "${YELLOW}[2/7] 创建 openclaw-vms 存储池...${NC}"
POOL_DIR="/var/lib/libvirt/images/openclaw-vms"

if virsh pool-info openclaw-vms &>/dev/null; then
  echo -e "${GREEN}✓ 存储池已存在${NC}"
else
  echo "创建存储池目录..."
  sudo mkdir -p "$POOL_DIR"
  sudo chown libvirt-qemu:kvm "$POOL_DIR"
  sudo chmod 775 "$POOL_DIR"
  
  echo "定义并启动存储池..."
  virsh pool-define-as openclaw-vms dir --target "$POOL_DIR"
  virsh pool-build openclaw-vms
  virsh pool-start openclaw-vms
  virsh pool-autostart openclaw-vms
  
  echo -e "${GREEN}✓ 存储池创建成功${NC}"
fi

# 3. 准备基础镜像
echo ""
echo -e "${YELLOW}[3/7] 准备基础镜像...${NC}"
BASE_IMAGE="/var/lib/libvirt/images/base.qcow2"

if [ -f "$BASE_IMAGE" ]; then
  echo -e "${GREEN}✓ 基础镜像已存在${NC}"
else
  echo "下载 Ubuntu 22.04 cloud image（约 500MB）..."
  sudo wget -q --show-progress \
    https://cloud-images.ubuntu.com/minimal/releases/jammy/release/ubuntu-22.04-minimal-cloudimg-amd64.img \
    -O "$BASE_IMAGE"
  
  sudo chown libvirt-qemu:kvm "$BASE_IMAGE"
  sudo chmod 664 "$BASE_IMAGE"
  
  echo -e "${GREEN}✓ 基础镜像下载完成${NC}"
fi

# 4. 配置用户权限
echo ""
echo -e "${YELLOW}[4/7] 配置用户权限...${NC}"
CURRENT_USER=$(whoami)

if groups "$CURRENT_USER" | grep -q '\blibvirt\b'; then
  echo -e "${GREEN}✓ 用户已在 libvirt 组${NC}"
else
  echo "将用户加入 libvirt 和 kvm 组..."
  sudo usermod -aG libvirt "$CURRENT_USER"
  sudo usermod -aG kvm "$CURRENT_USER"
  echo -e "${YELLOW}! 需要重新登录才能生效${NC}"
fi

# 5. 检查网络
echo ""
echo -e "${YELLOW}[5/7] 检查 Libvirt 网络...${NC}"
if virsh net-info default &>/dev/null; then
  if virsh net-info default | grep -q "Active:.*yes"; then
    echo -e "${GREEN}✓ default 网络已激活${NC}"
  else
    echo "启动 default 网络..."
    virsh net-start default
    virsh net-autostart default
    echo -e "${GREEN}✓ default 网络已启动${NC}"
  fi
else
  echo -e "${RED}✗ default 网络不存在${NC}"
  exit 1
fi

# 6. 配置后端
echo ""
echo -e "${YELLOW}[6/7] 配置后端 .env 文件...${NC}"
ENV_FILE="$(dirname "$0")/backend/.env"

if [ -f "$ENV_FILE" ]; then
  if grep -q "ENABLE_LIBVIRT=true" "$ENV_FILE"; then
    echo -e "${GREEN}✓ ENABLE_LIBVIRT 已配置${NC}"
  else
    echo "添加 ENABLE_LIBVIRT=true 到 .env..."
    echo "" >> "$ENV_FILE"
    echo "# Libvirt Integration" >> "$ENV_FILE"
    echo "ENABLE_LIBVIRT=true" >> "$ENV_FILE"
    echo -e "${GREEN}✓ 配置已添加${NC}"
  fi
else
  echo -e "${RED}✗ .env 文件不存在：$ENV_FILE${NC}"
  exit 1
fi

# 7. 重启后端服务（可选）
echo ""
echo -e "${YELLOW}[7/7] 重启后端服务...${NC}"
read -p "是否重启后端服务？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "停止后端服务..."
  pkill -f "uvicorn app.main:app" || true
  sleep 2
  
  echo "启动后端服务..."
  cd "$(dirname "$0")/backend"
  source venv/bin/activate
  nohup uvicorn app.main:app --host 0.0.0.0 --port 9000 > /tmp/openclaw-backend.log 2>&1 &
  
  echo -e "${GREEN}✓ 后端服务已重启${NC}"
  echo "日志文件：/tmp/openclaw-backend.log"
else
  echo -e "${YELLOW}跳过重启，请手动重启后端服务${NC}"
fi

# 完成
echo ""
echo "========================================="
echo -e "${GREEN}✓ Libvirt 环境准备完成！${NC}"
echo "========================================="
echo ""
echo "下一步："
echo "1. 如果修改了用户组，请重新登录"
echo "2. 运行测试脚本验证："
echo "   python3 test_libvirt_integration.py"
echo "3. 检查 Libvirt 中的 VM："
echo "   virsh list --all"
echo "4. 查看后端日志："
echo "   tail -f /tmp/openclaw-backend.log"
echo ""
