"""
SSH client for remote VM deployment and configuration.
"""
import asyncssh
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.exceptions import VMOperationError


class DeployConfig:
    """Deployment configuration."""
    
    def __init__(
        self,
        agents: list = None,
        openclaw_version: str = "latest"
    ):
        self.agents = agents or []
        self.openclaw_version = openclaw_version


class SSHClient:
    """
    SSH client for VM deployment automation.
    
    Handles OpenClaw installation, configuration, and management.
    """
    
    def __init__(self):
        self.key_path = settings.SSH_PRIVATE_KEY_PATH
        self.user = settings.SSH_USER
    
    async def connect(self, ip: str):
        """
        Establish SSH connection.
        
        Args:
            ip: Target IP address
            
        Returns:
            asyncssh.SSHClientConnection
            
        Raises:
            VMOperationError: If connection fails
        """
        try:
            conn = await asyncssh.connect(
                ip,
                username=self.user,
                client_keys=[self.key_path],
                known_hosts=None  # In production, use proper host key verification
            )
            return conn
        except Exception as e:
            raise VMOperationError("ssh_connect", f"Failed to connect to {ip}: {str(e)}")
    
    async def deploy_openclaw(self, ip: str, config: DeployConfig) -> None:
        """
        Deploy OpenClaw to a VM.
        
        Args:
            ip: VM IP address
            config: Deployment configuration
            
        Raises:
            VMOperationError: If deployment fails
        """
        try:
            async with await self.connect(ip) as conn:
                # Update system
                await conn.run('apt-get update && apt-get upgrade -y', check=True)
                
                # Install dependencies
                await conn.run(
                    'apt-get install -y nodejs npm docker.io curl wget',
                    check=True
                )
                
                # Install OpenClaw
                await conn.run('npm install -g openclaw', check=True)
                
                # Initialize OpenClaw
                await conn.run('openclaw init', check=True)
                
                # Configure agents
                for agent_config in config.agents:
                    await self._configure_agent(conn, agent_config)
                
                # Enable and start service
                await conn.run('systemctl enable openclaw-gateway', check=True)
                await conn.run('systemctl start openclaw-gateway', check=True)
                
                # Verify service is running
                result = await conn.run('systemctl is-active openclaw-gateway')
                if result.exit_status != 0:
                    raise VMOperationError("deploy", "OpenClaw service failed to start")
                
        except Exception as e:
            raise VMOperationError("deploy", str(e))
    
    async def _configure_agent(self, conn, agent_config: Dict[str, Any]) -> None:
        """
        Configure an agent on the VM.
        
        Args:
            conn: SSH connection
            agent_config: Agent configuration
        """
        # Write agent configuration
        import json
        config_json = json.dumps(agent_config)
        await conn.run(f'openclaw agent create --config \'{config_json}\'', check=True)
    
    async def configure_channel(self, ip: str, channel_type: str, channel_config: Dict[str, Any]) -> None:
        """
        Configure a channel on the VM.
        
        Args:
            ip: VM IP address
            channel_type: Type of channel (feishu, telegram, etc.)
            channel_config: Channel configuration
            
        Raises:
            VMOperationError: If configuration fails
        """
        try:
            async with await self.connect(ip) as conn:
                import json
                config_json = json.dumps(channel_config)
                await conn.run(f'openclaw config set channels.{channel_type} \'{config_json}\'', check=True)
                await conn.run('systemctl restart openclaw-gateway', check=True)
        except Exception as e:
            raise VMOperationError("configure_channel", str(e))
    
    async def get_agent_status(self, ip: str, agent_id: str) -> Dict[str, Any]:
        """
        Get agent status from VM.
        
        Args:
            ip: VM IP address
            agent_id: Agent ID
            
        Returns:
            Agent status information
            
        Raises:
            VMOperationError: If status retrieval fails
        """
        try:
            async with await self.connect(ip) as conn:
                result = await conn.run(f'openclaw agent status {agent_id}', check=True)
                import json
                return json.loads(result.stdout)
        except Exception as e:
            raise VMOperationError("agent_status", str(e))
    
    async def execute_command(self, ip: str, command: str) -> str:
        """
        Execute arbitrary command on VM.
        
        Args:
            ip: VM IP address
            command: Command to execute
            
        Returns:
            Command output
            
        Raises:
            VMOperationError: If execution fails
        """
        try:
            async with await self.connect(ip) as conn:
                result = await conn.run(command, check=True)
                return result.stdout
        except Exception as e:
            raise VMOperationError("execute", str(e))


# Global instance
ssh_client = SSHClient()
