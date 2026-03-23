"""
Tests for Libvirt VM integration (mock mode).
"""
import pytest
import asyncio
from app.infrastructure.vm.libvirt_manager import (
    libvirt_manager,
    LibvirtManager,
    VMSpec,
    VMInfo
)
from app.infrastructure.vm.ssh_deployer import (
    ssh_deployer,
    SSHDeployer,
    DeployConfig
)


class TestLibvirtManager:
    """Test LibvirtManager in simulation mode."""
    
    @pytest.mark.asyncio
    async def test_create_vm(self):
        """Test VM creation in mock mode."""
        spec = VMSpec(
            name="test-vm-001",
            cpu=2,
            memory=2048,
            disk=20
        )
        
        vm_info = await libvirt_manager.create_vm(spec)
        
        assert vm_info.id is not None
        assert vm_info.name == "test-vm-001"
        assert vm_info.status == "stopped"
        assert vm_info.ip_address is None
    
    @pytest.mark.asyncio
    async def test_start_vm(self):
        """Test VM start in mock mode."""
        # Create VM first
        spec = VMSpec(
            name="test-vm-002",
            cpu=2,
            memory=2048,
            disk=20
        )
        vm_info = await libvirt_manager.create_vm(spec)
        
        # Start VM
        result = await libvirt_manager.start_vm(vm_info.id)
        
        assert result is True
        
        # Check status
        status = await libvirt_manager.get_vm_status(vm_info.id)
        assert status["status"] == "running"
        assert status["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_get_vm_ip(self):
        """Test getting VM IP address in mock mode."""
        # Create and start VM
        spec = VMSpec(
            name="test-vm-003",
            cpu=2,
            memory=2048,
            disk=20
        )
        vm_info = await libvirt_manager.create_vm(spec)
        await libvirt_manager.start_vm(vm_info.id)
        
        # Get IP
        ip_address = await libvirt_manager.get_vm_ip(vm_info.id)
        
        assert ip_address is not None
        assert ip_address.startswith("192.168.122.")
    
    @pytest.mark.asyncio
    async def test_stop_vm(self):
        """Test VM stop in mock mode."""
        # Create and start VM
        spec = VMSpec(
            name="test-vm-004",
            cpu=2,
            memory=2048,
            disk=20
        )
        vm_info = await libvirt_manager.create_vm(spec)
        await libvirt_manager.start_vm(vm_info.id)
        
        # Stop VM
        result = await libvirt_manager.stop_vm(vm_info.id)
        
        assert result is True
        
        # Check status
        status = await libvirt_manager.get_vm_status(vm_info.id)
        assert status["status"] == "stopped"
        assert status["is_active"] is False
    
    @pytest.mark.asyncio
    async def test_delete_vm(self):
        """Test VM deletion in mock mode."""
        # Create VM
        spec = VMSpec(
            name="test-vm-005",
            cpu=2,
            memory=2048,
            disk=20
        )
        vm_info = await libvirt_manager.create_vm(spec)
        
        # Delete VM
        result = await libvirt_manager.delete_vm(vm_info.id)
        
        assert result is True
        
        # Try to get status (should fail)
        with pytest.raises(Exception):
            await libvirt_manager.get_vm_status(vm_info.id)
    
    @pytest.mark.asyncio
    async def test_get_vm_status(self):
        """Test getting VM status in mock mode."""
        # Create VM
        spec = VMSpec(
            name="test-vm-006",
            cpu=2,
            memory=2048,
            disk=20
        )
        vm_info = await libvirt_manager.create_vm(spec)
        
        # Get status
        status = await libvirt_manager.get_vm_status(vm_info.id)
        
        assert "status" in status
        assert "cpu_percent" in status
        assert "memory_percent" in status
        assert "is_active" in status
        assert status["status"] == "stopped"


class TestSSHDeployer:
    """Test SSHDeployer in simulation mode."""
    
    @pytest.mark.asyncio
    async def test_deploy_openclaw(self):
        """Test OpenClaw deployment in mock mode."""
        config = DeployConfig(
            agents=[
                {
                    "name": "test-agent",
                    "model": "gpt-3.5-turbo",
                    "system_prompt": "You are a helpful assistant."
                }
            ],
            openclaw_version="latest",
            install_docker=True
        )
        
        result = await ssh_deployer.deploy_openclaw(
            host="192.168.122.100",
            config=config
        )
        
        assert result["status"] == "success"
        assert result["host"] == "192.168.122.100"
        assert result["agents_configured"] == 1
        assert len(result["logs"]) > 0
    
    @pytest.mark.asyncio
    async def test_check_openclaw_health(self):
        """Test OpenClaw health check in mock mode."""
        result = await ssh_deployer.check_openclaw_health("192.168.122.100")
        
        assert "host" in result
        assert "is_healthy" in result
        assert result["host"] == "192.168.122.100"
    
    @pytest.mark.asyncio
    async def test_configure_channel(self):
        """Test channel configuration in mock mode."""
        result = await ssh_deployer.configure_channel(
            host="192.168.122.100",
            channel_type="telegram",
            channel_config={
                "bot_token": "test_token",
                "allowed_users": [123456]
            }
        )
        
        assert result["status"] == "success"
        assert result["channel_type"] == "telegram"


class TestVMProvisioningFlow:
    """Test complete VM provisioning flow."""
    
    @pytest.mark.asyncio
    async def test_full_provisioning_flow(self):
        """Test complete VM provisioning workflow."""
        # Step 1: Create VM
        spec = VMSpec(
            name="test-vm-full",
            cpu=2,
            memory=2048,
            disk=20,
            cloud_init_config={
                "hostname": "test-vm-full",
                "users": [{"name": "root"}]
            }
        )
        
        vm_info = await libvirt_manager.create_vm(spec)
        assert vm_info.id is not None
        
        # Step 2: Start VM
        await libvirt_manager.start_vm(vm_info.id)
        status = await libvirt_manager.get_vm_status(vm_info.id)
        assert status["status"] == "running"
        
        # Step 3: Get IP
        ip_address = await libvirt_manager.get_vm_ip(vm_info.id)
        assert ip_address is not None
        
        # Step 4: Deploy OpenClaw
        config = DeployConfig(openclaw_version="latest")
        deploy_result = await ssh_deployer.deploy_openclaw(ip_address, config=config)
        assert deploy_result["status"] == "success"
        
        # Step 5: Verify health
        health = await ssh_deployer.check_openclaw_health(ip_address)
        assert health["is_healthy"] is True
        
        # Cleanup
        await libvirt_manager.stop_vm(vm_info.id)
        await libvirt_manager.delete_vm(vm_info.id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
