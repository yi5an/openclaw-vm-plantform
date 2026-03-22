"""
Libvirt integration for VM management.
"""
import libvirt
from typing import Optional, Dict, Any
from contextlib import contextmanager
from app.core.config import settings
from app.core.exceptions import VMOperationError


class VMSpec:
    """VM specification for creation."""
    
    def __init__(
        self,
        name: str,
        cpu: int,
        memory: int,
        disk: int,
        base_image: Optional[str] = None
    ):
        self.name = name
        self.cpu = cpu
        self.memory = memory  # MB
        self.disk = disk      # GB
        self.base_image = base_image or settings.VM_BASE_IMAGE_PATH


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
    """
    
    def __init__(self):
        self.uri = settings.LIBVIRT_URI
        self.pool_name = settings.LIBVIRT_POOL_NAME
        self.network_name = settings.LIBVIRT_NETWORK_NAME
    
    @contextmanager
    def get_connection(self):
        """
        Get Libvirt connection with context manager.
        
        Yields:
            libvirt.virConnect: Libvirt connection
            
        Raises:
            VMOperationError: If connection fails
        """
        conn = None
        try:
            conn = libvirt.open(self.uri)
            if conn is None:
                raise VMOperationError("connect", f"Failed to connect to libvirt at {self.uri}")
            yield conn
        except libvirt.libvirtError as e:
            raise VMOperationError("connect", str(e))
        finally:
            if conn:
                conn.close()
    
    def _generate_vm_xml(self, spec: VMSpec) -> str:
        """
        Generate VM XML configuration.
        
        Args:
            spec: VM specification
            
        Returns:
            XML string for VM definition
        """
        return f"""
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
            <interface type='network'>
              <source network='{self.network_name}'/>
              <model type='virtio'/>
            </interface>
            <serial type='pty'/>
            <console type='pty'/>
          </devices>
        </domain>
        """
    
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
            with self.get_connection() as conn:
                # Generate XML
                xml = self._generate_vm_xml(spec)
                
                # Define domain
                domain = conn.defineXML(xml)
                if domain is None:
                    raise VMOperationError("create", "Failed to define VM domain")
                
                # TODO: Create disk image using qemu-img
                # TODO: Start the domain
                # TODO: Wait for IP assignment
                
                return VMInfo(
                    id=domain.UUIDString(),
                    name=domain.name(),
                    status="stopped"
                )
        except Exception as e:
            raise VMOperationError("create", str(e))
    
    async def start_vm(self, vm_id: str) -> None:
        """
        Start a virtual machine.
        
        Args:
            vm_id: VM UUID
            
        Raises:
            VMOperationError: If start fails
        """
        try:
            with self.get_connection() as conn:
                domain = conn.lookupByUUIDString(vm_id)
                if domain is None:
                    raise VMOperationError("start", f"VM {vm_id} not found")
                
                domain.create()
        except Exception as e:
            raise VMOperationError("start", str(e))
    
    async def stop_vm(self, vm_id: str) -> None:
        """
        Stop a virtual machine.
        
        Args:
            vm_id: VM UUID
            
        Raises:
            VMOperationError: If stop fails
        """
        try:
            with self.get_connection() as conn:
                domain = conn.lookupByUUIDString(vm_id)
                if domain is None:
                    raise VMOperationError("stop", f"VM {vm_id} not found")
                
                domain.shutdown()
        except Exception as e:
            raise VMOperationError("stop", str(e))
    
    async def delete_vm(self, vm_id: str) -> None:
        """
        Delete a virtual machine.
        
        Args:
            vm_id: VM UUID
            
        Raises:
            VMOperationError: If deletion fails
        """
        try:
            with self.get_connection() as conn:
                domain = conn.lookupByUUIDString(vm_id)
                if domain is None:
                    raise VMOperationError("delete", f"VM {vm_id} not found")
                
                # Destroy if running
                if domain.isActive():
                    domain.destroy()
                
                # Undefine
                domain.undefine()
                
                # TODO: Delete disk image
        except Exception as e:
            raise VMOperationError("delete", str(e))
    
    async def get_vm_status(self, vm_id: str) -> Dict[str, Any]:
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
            with self.get_connection() as conn:
                domain = conn.lookupByUUIDString(vm_id)
                if domain is None:
                    raise VMOperationError("status", f"VM {vm_id} not found")
                
                # Get status
                is_active = domain.isActive()
                status = "running" if is_active else "stopped"
                
                # Get CPU and memory stats if running
                cpu_percent = 0.0
                memory_percent = 0.0
                
                if is_active:
                    # CPU stats
                    cpu_stats = domain.getCPUStats(True)[0]
                    # Simplified CPU percentage calculation
                    cpu_percent = min(cpu_stats.get('cpu_time', 0) / 1000000000, 100.0)
                    
                    # Memory stats
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
            raise VMOperationError("status", str(e))


# Global instance
libvirt_manager = LibvirtManager()
