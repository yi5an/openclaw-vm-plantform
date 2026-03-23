#!/usr/bin/env python3
"""
Libvirt 集成测试脚本

测试内容：
1. Libvirt 环境检查
2. LibvirtManager 功能测试
3. VM API + Libvirt 集成测试
4. 错误处理测试
"""

import sys
import os
import json
import time
import requests
from typing import Optional, Dict, Any

# 添加 backend 到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# 配置
API_BASE = "http://localhost:9000/api/v1"
TEST_USER = {
    "email": "libvirt-test@example.com",
    "password": "TestPass123!",
    "username": "libvirt-tester"
}

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(msg: str):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{msg}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_info(msg: str):
    print(f"{Colors.YELLOW}ℹ️  {msg}{Colors.END}")

def print_test(test_name: str, passed: bool, details: str = ""):
    status = f"{Colors.GREEN}PASS{Colors.END}" if passed else f"{Colors.RED}FAIL{Colors.END}"
    print(f"  [{status}] {test_name}")
    if details:
        print(f"         {details}")


class LibvirtIntegrationTester:
    """Libvirt 集成测试器"""
    
    def __init__(self):
        self.token: Optional[str] = None
        self.test_vm_id: Optional[str] = None
        self.plan_id: Optional[str] = None
        
    def run_all_tests(self):
        """运行所有测试"""
        print_header("Libvirt 集成测试")
        
        # 1. 环境检查
        self.test_1_environment_check()
        
        # 2. LibvirtManager 测试
        self.test_2_libvirt_manager()
        
        # 3. 用户认证
        if not self.test_3_authentication():
            print_error("认证失败，无法继续测试")
            return
        
        # 4. 获取 Plan
        if not self.test_4_get_plans():
            print_error("无法获取套餐，无法继续测试")
            return
        
        # 5. VM 创建测试
        self.test_5_vm_creation()
        
        # 6. VM 操作测试
        if self.test_vm_id:
            self.test_6_vm_operations()
        
        # 7. 错误处理测试
        self.test_7_error_handling()
        
        # 8. 清理
        self.cleanup()
        
        # 总结
        self.print_summary()
    
    def test_1_environment_check(self):
        """测试 1: Libvirt 环境检查"""
        print_header("测试 1: Libvirt 环境检查")
        
        # 检查 virsh 命令
        try:
            import subprocess
            result = subprocess.run(['virsh', '--version'], capture_output=True, text=True)
            print_test("virsh 命令可用", result.returncode == 0, f"版本: {result.stdout.strip()}")
        except Exception as e:
            print_test("virsh 命令可用", False, str(e))
        
        # 检查 Python libvirt 模块
        try:
            import libvirt
            version = getattr(libvirt, '__version__', '已安装')
            print_test("Python libvirt 模块", True, f"版本: {version}")
        except ImportError as e:
            print_test("Python libvirt 模块", False, str(e))
        
        # 检查 Libvirt 连接
        try:
            import libvirt
            conn = libvirt.open('qemu:///system')
            print_test("Libvirt 连接", conn is not None, f"主机: {conn.getHostname()}")
            
            # 检查存储池
            pools = conn.listAllStoragePools()
            print_test("存储池可用", len(pools) > 0, f"数量: {len(pools)}")
            
            # 检查网络
            networks = conn.listAllNetworks()
            print_test("网络可用", len(networks) > 0, f"数量: {len(networks)}")
            
            conn.close()
        except Exception as e:
            print_test("Libvirt 连接", False, str(e))
        
        # 检查后端配置
        try:
            from app.core.config import settings
            print_test("ENABLE_LIBVIRT 配置", hasattr(settings, 'ENABLE_LIBVIRT'), 
                      f"值: {getattr(settings, 'ENABLE_LIBVIRT', 'N/A')}")
            print_test("LIBVIRT_URI 配置", hasattr(settings, 'LIBVIRT_URI'),
                      f"值: {getattr(settings, 'LIBVIRT_URI', 'N/A')}")
        except Exception as e:
            print_test("后端配置加载", False, str(e))
    
    def test_2_libvirt_manager(self):
        """测试 2: LibvirtManager 功能测试"""
        print_header("测试 2: LibvirtManager 功能测试")
        
        try:
            from app.infrastructure.vm.libvirt_manager import LibvirtManager, VMSpec
            
            manager = LibvirtManager()
            print_test("LibvirtManager 初始化", True)
            
            # 测试连接
            try:
                with manager.get_connection() as conn:
                    print_test("LibvirtManager 连接", conn is not None)
            except Exception as e:
                print_test("LibvirtManager 连接", False, str(e))
            
            # 测试 VMSpec 创建
            try:
                spec = VMSpec(
                    name="test-vm-spec",
                    cpu=1,
                    memory=2048,
                    disk=20
                )
                print_test("VMSpec 创建", True, f"配置: {spec.cpu}核/{spec.memory}MB/{spec.disk}GB")
            except Exception as e:
                print_test("VMSpec 创建", False, str(e))
            
        except Exception as e:
            print_test("LibvirtManager 导入", False, str(e))
    
    def test_3_authentication(self) -> bool:
        """测试 3: 用户认证"""
        print_header("测试 3: 用户认证")
        
        # 尝试登录
        try:
            response = requests.post(
                f"{API_BASE}/auth/login",
                data={
                    "username": TEST_USER["email"],
                    "password": TEST_USER["password"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["data"]["access_token"]
                print_test("用户登录", True)
                return True
            elif response.status_code == 401:
                # 用户不存在，尝试注册
                print_info("用户不存在，尝试注册...")
                response = requests.post(
                    f"{API_BASE}/auth/register",
                    json=TEST_USER
                )
                
                if response.status_code in [200, 201]:
                    print_test("用户注册", True)
                    # 重新登录
                    response = requests.post(
                        f"{API_BASE}/auth/login",
                        data={
                            "username": TEST_USER["email"],
                            "password": TEST_USER["password"]
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        self.token = data["data"]["access_token"]
                        print_test("用户登录", True)
                        return True
                
            print_test("用户认证", False, response.text)
            return False
            
        except Exception as e:
            print_test("用户认证", False, str(e))
            return False
    
    def test_4_get_plans(self) -> bool:
        """测试 4: 获取套餐列表"""
        print_header("测试 4: 获取套餐列表")
        
        try:
            response = requests.get(
                f"{API_BASE}/vms/plans",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                plans = data["data"]
                print_test("获取套餐列表", True, f"数量: {len(plans)}")
                
                if plans:
                    self.plan_id = plans[0]["id"]
                    print_info(f"使用套餐: {plans[0]['name']} (ID: {self.plan_id})")
                    return True
                else:
                    print_test("套餐列表", False, "没有可用套餐")
                    return False
            else:
                print_test("获取套餐列表", False, response.text)
                return False
                
        except Exception as e:
            print_test("获取套餐列表", False, str(e))
            return False
    
    def test_5_vm_creation(self):
        """测试 5: VM 创建流程"""
        print_header("测试 5: VM 创建流程")
        
        # 创建 VM
        try:
            response = requests.post(
                f"{API_BASE}/vms",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "name": f"libvirt-test-{int(time.time())}",
                    "plan_id": self.plan_id,
                    "region": "default"
                }
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.test_vm_id = data["data"]["id"]
                status = data["data"]["status"]
                print_test("VM 创建请求", True, f"ID: {self.test_vm_id}, 状态: {status}")
                
                # 检查状态是否为 creating
                print_test("VM 初始状态", status == "creating", f"状态: {status}")
                
                # 等待并检查状态变化
                print_info("等待 5 秒后检查状态...")
                time.sleep(5)
                
                response = requests.get(
                    f"{API_BASE}/vms/{self.test_vm_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    current_status = data["data"]["status"]
                    print_test("VM 状态查询", True, f"当前状态: {current_status}")
                    
                    # 检查是否调用了 Libvirt（通过日志或状态变化）
                    if current_status in ["creating", "running"]:
                        print_info(f"✓ 状态正常（{current_status}）")
                    else:
                        print_info(f"⚠ 状态异常（{current_status}）")
                else:
                    print_test("VM 状态查询", False, response.text)
                    
            else:
                print_test("VM 创建请求", False, response.text)
                
        except Exception as e:
            print_test("VM 创建流程", False, str(e))
    
    def test_6_vm_operations(self):
        """测试 6: VM 操作（启动/停止/删除）"""
        print_header("测试 6: VM 操作测试")
        
        # 启动 VM
        try:
            response = requests.post(
                f"{API_BASE}/vms/{self.test_vm_id}/start",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data["data"]["status"]
                print_test("VM 启动", True, f"状态: {status}")
            else:
                print_test("VM 启动", False, response.text)
        except Exception as e:
            print_test("VM 启动", False, str(e))
        
        # 停止 VM
        try:
            response = requests.post(
                f"{API_BASE}/vms/{self.test_vm_id}/stop",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data["data"]["status"]
                print_test("VM 停止", True, f"状态: {status}")
            else:
                print_test("VM 停止", False, response.text)
        except Exception as e:
            print_test("VM 停止", False, str(e))
    
    def test_7_error_handling(self):
        """测试 7: 错误处理"""
        print_header("测试 7: 错误处理测试")
        
        # 测试无效 VM ID
        try:
            response = requests.get(
                f"{API_BASE}/vms/invalid-uuid-123",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            print_test("无效 UUID 处理", response.status_code == 404,
                      f"状态码: {response.status_code}")
        except Exception as e:
            print_test("无效 UUID 处理", False, str(e))
        
        # 测试无权限访问
        try:
            # 使用另一个用户的 token（如果没有，跳过）
            response = requests.get(
                f"{API_BASE}/vms/{self.test_vm_id}",
                headers={"Authorization": "Bearer invalid-token"}
            )
            print_test("无权限访问处理", response.status_code == 401,
                      f"状态码: {response.status_code}")
        except Exception as e:
            print_test("无权限访问处理", False, str(e))
        
        # 测试重复创建
        try:
            response = requests.post(
                f"{API_BASE}/vms",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "name": "duplicate-test-vm",
                    "plan_id": self.plan_id
                }
            )
            
            if response.status_code in [200, 201]:
                # 第二次创建同名 VM
                response2 = requests.post(
                    f"{API_BASE}/vms",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "name": "duplicate-test-vm",
                        "plan_id": self.plan_id
                    }
                )
                print_test("重复创建处理", response2.status_code == 409,
                          f"状态码: {response2.status_code}")
                
                # 清理
                if response.status_code in [200, 201]:
                    vm_id = response.json()["data"]["id"]
                    requests.delete(
                        f"{API_BASE}/vms/{vm_id}",
                        headers={"Authorization": f"Bearer {self.token}"}
                    )
        except Exception as e:
            print_test("重复创建处理", False, str(e))
    
    def cleanup(self):
        """清理测试数据"""
        print_header("清理测试数据")
        
        if self.test_vm_id:
            try:
                response = requests.delete(
                    f"{API_BASE}/vms/{self.test_vm_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                print_test("删除测试 VM", response.status_code == 200,
                          f"ID: {self.test_vm_id}")
            except Exception as e:
                print_test("删除测试 VM", False, str(e))
    
    def print_summary(self):
        """打印测试总结"""
        print_header("测试总结")
        print_info("Libvirt 集成测试完成")
        print_info(f"测试 VM ID: {self.test_vm_id}")
        print()
        print_info("下一步建议:")
        print("  1. 检查后端日志，确认是否调用了 LibvirtManager")
        print("  2. 如果未调用，需要修改 VM API 端点集成 LibvirtManager")
        print("  3. 启用 ENABLE_LIBVIRT=true 进行真实模式测试")
        print("  4. 准备基础镜像 (VM_BASE_IMAGE_PATH)")
        print("  5. 配置存储池 (LIBVIRT_POOL_NAME)")
        print("  6. 配置网络 (LIBVIRT_NETWORK_NAME)")


if __name__ == "__main__":
    tester = LibvirtIntegrationTester()
    tester.run_all_tests()
