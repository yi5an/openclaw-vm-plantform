"""
Libvirt integration for VM management.
"""
import libvirt
import uuid
import asyncio
import logging
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager
from app.core.config import settings
from app.core.exceptions import VMOperationError

logger = logging.getLogger(__name__)


class VMSpec:
    """VM specification for creation."""
    
    def __init__(
        self,
        name: str,
        cpu: int,
        memory: int,
        disk: int,
        base_image: Optional[str] = None,
        cloud_init_config: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.cpu = cpu
        self.memory = memory  # MB
        self.disk = disk      # GB
        self.base_image = base_image or settings.VM_BASE_IMAGE_PATH
        self.cloud_init_config = cloud_init_config or {}


class VMInfo:
    """VM information."""
    
    def __init__(
        self,
        id: str,
        name: str,
        status: str,
        ip_address: Optional[str] = None,
        cpu_percent: float = 0.0,
        memory_percent: float = 0.0
    ):
        self.id = id
        self.name = name
        self.status = status
        self.ip_address = ip_address
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent


class LibvirtManager:
    """
    Libvirt connection manager for VM operations.
    
    Handles VM creation, deletion, start, stop, and status monitoring.
    Supports simulation mode when ENABLE_LIBVIRT=False.
    """
    
    def __init__(self):
        self.uri = settings.LIBVIRT_URI
        self.pool_name = settings.LIBVIRT_POOL_NAME
        self.network_name = settings.LIBVIRT_NETWORK_NAME
        self.enable_libvirt = settings.ENABLE_LIBVIRT
        
        # 模拟数据存储
        self._mock_vms: Dict[str, Dict[str, Any]] = {}
        
        if self.enable_libvirt:
            logger.info("Libvirt integration enabled (real mode)")
        else:
            logger.info("Libvirt integration disabled (simulation mode)")
    
    @contextmanager
    def get_connection(self):
        """
        Get Libvirt connection with context manager.
        
        Yields:
            libvirt.virConnect: Libvirt connection
            
        Raises:
            VMOperationError: If connection fails
        """
        if not self.enable_libvirt:
            # 模拟模式：返回 None
            yield None
            return
        
        conn = None
        try:
            conn = libvirt.open(self.uri)
            if conn is None:
                raise VMOperationError("connect", f"Failed to connect to libvirt at {self.uri}")
            yield conn
        except libvirt.libvirtError as e:
            logger.error(f"Libvirt connection error: {e}")
            raise VMOperationError("connect", str(e))
        finally:
            if conn:
                conn.close()
    
    def _generate_cloud_init_iso(self, spec: VMSpec) -> str:
        """
        Generate cloud-init ISO path for VM.
        
        Args:
            spec: VM specification
            
        Returns:
            Path to cloud-init ISO
        """
        # TODO: 实际生成 cloud-init ISO
        # 1. 创建 meta-data 和 user-data 文件
        # 2. 使用 genisoimage 或 cloud-localds 生成 ISO
        # 3. 返回 ISO 路径
        
        iso_path = f"/var/lib/libvirt/cloud-init/{spec.name}-cidata.iso"
        logger.info(f"[Mock] Generated cloud-init ISO at {iso_path}")
        return iso_path
    
    def _generate_vm_xml(self, spec: VMSpec, cloud_init_iso: str = None) -> str:
        """
        Generate VM XML configuration.
        
        Args:
            spec: VM specification
            cloud_init_iso: Path to cloud-init ISO
            
        Returns:
            XML string for VM definition
        """
        # 基础 XML
        xml = f"""
        <domain type='kvm'>
          <name>{spec.name}</name>
          <memory unit='MiB'>{spec.memory}</memory>
          <vcpu>{spec.cpu}</vcpu>
          <os>
            <type arch='x86_64'>hvm</type>
            <boot dev='hd'/>
          </os>
          <features>
            <acpi/>
            <apic/>
          </features>
          <cpu mode='host-passthrough'/>
          <devices>
            <disk type='file' device='disk'>
              <driver name='qemu' type='qcow2'/>
              <source file='/var/lib/libvirt/images/{spec.name}.qcow2'/>
              <target dev='vda' bus='virtio'/>
            </disk>
        """
        
        # 添加 cloud-init ISO
        if cloud_init_iso:
            xml += f"""
            <disk type='file' device='cdrom'>
              <driver name='qemu' type='raw'/>
              <source file='{cloud_init_iso}'/>
              <target dev='hda' bus='ide'/>
              <readonly/>
            </disk>
            """
        
        # 添加网络接口
        xml += f"""
            <interface type='network'>
              <mac address='52:54:00:{uuid.uuid4().hex[:6]}'/>
              <source network='{self.network_name}'/>
              <model type='virtio'/>
            </interface>
            <serial type='pty'/>
            <console type='pty'/>
          </devices>
        </domain>
        """
        
        return xml
    
    async def create_vm(self, spec: VMSpec) -> VMInfo:
        """
        Create a new virtual machine.
        
        Args:
            spec: VM specification
            
        Returns:
            VM information
            
        Raises:
            VMOperationError: If creation fails
        """
        try:
            if not self.enable_libvirt:
                # 模拟模式
                logger.info(f"[Mock] Creating VM: {spec.name}")
                
                # 模拟延迟
                await asyncio.sleep(0.5)
                
                # 生成模拟 ID
                vm_id = str(uuid.uuid4())
                
                # 存储模拟数据
                self._mock_vms[vm_id] = {
                    "name": spec.name,
                    "status": "stopped",
                    "ip_address": None,
                    "spec": spec,
                    "created_at": time.time()
                }
                
                logger.info(f"[Mock] VM created successfully: {vm_id}")
                
                return VMInfo(
                    id=vm_id,
                    name=spec.name,
                    status="stopped"
                )
            
            # 真实模式
            with self.get_connection() as conn:
                # 生成 cloud-init ISO
                cloud_init_iso = self._generate_cloud_init_iso(spec)
                
                # 生成 XML
                xml = self._generate_vm_xml(spec, cloud_init_iso)
                
                # 定义 domain
                domain = conn.defineXML(xml)
                if domain is None:
                    raise VMOperationError("create", "Failed to define VM domain")
                
                # TODO: 创建 qcow2 镜像
                # TODO: 启动 domain
                # TODO: 等待 IP 分配
                
                logger.info(f"VM created successfully: {domain.UUIDString()}")
                
                return VMInfo(
                    id=domain.UUIDString(),
                    name=domain.name(),
                    status="stopped"
                )
        except Exception as e:
            logger.error(f"Failed to create VM: {e}")
            raise VMOperationError("create", str(e))
    
    async def start_vm(self, vm_id: str) -> bool:
        """
        Start a virtual machine.
        
        Args:
            vm_id: VM UUID
            
        Returns:
            True if successful
            
        Raises:
            VMOperationError: If start fails
        """
        try:
            if not self.enable_libvirt:
                # 模拟模式
                logger.info(f"[Mock] Starting VM: {vm_id}")
                
                if vm_id not in self._mock_vms:
                    raise VMOperationError("start", f"VM {vm_id} not found")
                
                await asyncio.sleep(0.3)
                
                self._mock_vms[vm_id]["status"] = "running"
                # 模拟 IP 分配
                self._mock_vms[vm_id]["ip_address"] = f"192.168.122.{100 + len(self._mock_vms)}"
                
                logger.info(f"[Mock] VM started successfully: {vm_id}")
                return True
            
            # 真实模式
            with self.get_connection() as conn:
                domain = conn.lookupByUUIDString(vm_id)
                if domain is None:
                    raise VMOperationError("start", f"VM {vm_id} not found")
                
                domain.create()
                logger.info(f"VM started successfully: {vm_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to start VM {vm_id}: {e}")
            raise VMOperationError("start", str(e))
    
    async def stop_vm(self, vm_id: str) -> bool:
        """
        Stop a virtual machine.
        
        Args:
            vm_id: VM UUID
            
        Returns:
            True if successful
            
        Raises:
            VMOperationError: If stop fails
        """
        try:
            if not self.enable_libvirt:
                # 模拟模式
                logger.info(f"[Mock] Stopping VM: {vm_id}")
                
                if vm_id not in self._mock_vms:
                    raise VMOperationError("stop", f"VM {vm_id} not found")
                
                await asyncio.sleep(0.3)
                
                self._mock_vms[vm_id]["status"] = "stopped"
                
                logger.info(f"[Mock] VM stopped successfully: {vm_id}")
                return True
            
            # 真实模式
            with self.get_connection() as conn:
                domain = conn.lookupByUUIDString(vm_id)
                if domain is None:
                    raise VMOperationError("stop", f"VM {vm_id} not found")
                
                domain.shutdown()
                logger.info(f"VM stopped successfully: {vm_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to stop VM {vm_id}: {e}")
            raise VMOperationError("stop", str(e))
    
    async def delete_vm(self, vm_id: str) -> bool:
        """
        Delete a virtual machine.
        
        Args:
            vm_id: VM UUID
            
        Returns:
            True if successful
            
        Raises:
            VMOperationError: If deletion fails
        """
        try:
            if not self.enable_libvirt:
                # 模拟模式
                logger.info(f"[Mock] Deleting VM: {vm_id}")
                
                if vm_id not in self._mock_vms:
                    raise VMOperationError("delete", f"VM {vm_id} not found")
                
                await asyncio.sleep(0.3)
                
                del self._mock_vms[vm_id]
                
                logger.info(f"[Mock] VM deleted successfully: {vm_id}")
                return True
            
            # 真实模式
            with self.get_connection() as conn:
                domain = conn.lookupByUUIDString(vm_id)
                if domain is None:
                    raise VMOperationError("delete", f"VM {vm_id} not found")
                
                # 强制停止（如果运行中）
                if domain.isActive():
                    domain.destroy()
                
                # 删除定义
                domain.undefine()
                
                # TODO: 删除磁盘镜像
                
                logger.info(f"VM deleted successfully: {vm_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete VM {vm_id}: {e}")
            raise VMOperationError("delete", str(e))
    
    async def get_vm_status(self, vm_id: str) -> dict:
        """
        Get VM status and resource usage.
        
        Args:
            vm_id: VM UUID
            
        Returns:
            Dictionary with VM status and metrics
            
        Raises:
            VMOperationError: If status retrieval fails
        """
        try:
            if not self.enable_libvirt:
                # 模拟模式
                logger.info(f"[Mock] Getting VM status: {vm_id}")
                
                if vm_id not in self._mock_vms:
                    raise VMOperationError("status", f"VM {vm_id} not found")
                
                vm_data = self._mock_vms[vm_id]
                
                # 模拟 CPU 和内存使用率
                import random
                cpu_percent = random.uniform(0, 50) if vm_data["status"] == "running" else 0.0
                memory_percent = random.uniform(20, 80) if vm_data["status"] == "running" else 0.0
                
                return {
                    "status": vm_data["status"],
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_percent": round(memory_percent, 2),
                    "is_active": vm_data["status"] == "running"
                }
            
            # 真实模式
            with self.get_connection() as conn:
                domain = conn.lookupByUUIDString(vm_id)
                if domain is None:
                    raise VMOperationError("status", f"VM {vm_id} not found")
                
                # 获取状态
                is_active = domain.isActive()
                status = "running" if is_active else "stopped"
                
                # 获取 CPU 和内存统计（如果运行中）
                cpu_percent = 0.0
                memory_percent = 0.0
                
                if is_active:
                    # CPU 统计
                    cpu_stats = domain.getCPUStats(True)[0]
                    cpu_percent = min(cpu_stats.get('cpu_time', 0) / 1000000000, 100.0)
                    
                    # 内存统计
                    mem_stats = domain.memoryStats()
                    if 'actual' in mem_stats and 'unused' in mem_stats:
                        memory_percent = ((mem_stats['actual'] - mem_stats['unused']) / mem_stats['actual']) * 100
                
                return {
                    "status": status,
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_percent": round(memory_percent, 2),
                    "is_active": is_active
                }
        except Exception as e:
            logger.error(f"Failed to get VM status {vm_id}: {e}")
            raise VMOperationError("status", str(e))
    
    async def get_vm_ip(self, vm_id: str) -> str:
        """
        Get VM IP address.
        
        Args:
            vm_id: VM UUID
            
        Returns:
            IP address string
            
        Raises:
            VMOperationError: If IP retrieval fails or VM not running
        """
        try:
            if not self.enable_libvirt:
                # 模拟模式
                logger.info(f"[Mock] Getting VM IP: {vm_id}")
                
                if vm_id not in self._mock_vms:
                    raise VMOperationError("get_ip", f"VM {vm_id} not found")
                
                vm_data = self._mock_vms[vm_id]
                
                if vm_data["status"] != "running":
                    raise VMOperationError("get_ip", "VM is not running")
                
                ip_address = vm_data["ip_address"]
                if not ip_address:
                    raise VMOperationError("get_ip", "IP address not assigned yet")
                
                logger.info(f"[Mock] VM IP: {ip_address}")
                return ip_address
            
            # 真实模式
            with self.get_connection() as conn:
                domain = conn.lookupByUUIDString(vm_id)
                if domain is None:
                    raise VMOperationError("get_ip", f"VM {vm_id} not found")
                
                if not domain.isActive():
                    raise VMOperationError("get_ip", "VM is not running")
                
                # 获取网络接口信息
                # 方法 1: 使用 QEMU Guest Agent
                # 方法 2: 使用 DHCP 租约
                # 方法 3: 使用 ARP 表
                
                # 这里使用 DHCP 租约方法（简化版）
                network = conn.networkLookupByName(self.network_name)
                leases = network.DHCPLeases()
                
                # 查找对应的 MAC 地址
                ifaces = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT, 0)
                if ifaces:
                    for iface_name, iface in ifaces.items():
                        for addr in iface['addrs']:
                            if addr['type'] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                                return addr['addr']
                
                # 如果 Guest Agent 不可用，尝试 DHCP 租约
                mac = None  # 从 domain XML 获取 MAC
                for lease in leases:
                    if lease['mac'] == mac:
                        return lease['ipaddr']
                
                raise VMOperationError("get_ip", "Could not determine IP address")
        except Exception as e:
            logger.error(f"Failed to get VM IP {vm_id}: {e}")
            raise VMOperationError("get_ip", str(e))


# Global instance
libvirt_manager = LibvirtManager()
