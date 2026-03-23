"""
SSH deployer for OpenClaw automated installation on VMs.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.exceptions import VMOperationError

logger = logging.getLogger(__name__)


class DeployConfig:
    """Deployment configuration."""
    
    def __init__(
        self,
        agents: Optional[List[Dict[str, Any]]] = None,
        openclaw_version: str = "latest",
        install_docker: bool = True,
        custom_scripts: Optional[List[str]] = None
    ):
        self.agents = agents or []
        self.openclaw_version = openclaw_version
        self.install_docker = install_docker
        self.custom_scripts = custom_scripts or []


class SSHDeployer:
    """
    SSH automated deployer for OpenClaw.
    
    Handles OpenClaw installation, configuration, and agent deployment on VMs.
    Supports simulation mode when ENABLE_LIBVIRT=False.
    """
    
    def __init__(self):
        self.key_path = settings.SSH_PRIVATE_KEY_PATH
        self.user = settings.SSH_USER
        self.connect_timeout = settings.SSH_CONNECT_TIMEOUT
        self.deploy_timeout = settings.SSH_DEPLOY_TIMEOUT
        self.enable_libvirt = settings.ENABLE_LIBVIRT
    
    async def _execute_ssh_command(self, host: str, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute SSH command (mock or real).
        
        Args:
            host: Target host IP
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Dict with exit_code, stdout, stderr
            
        Raises:
            VMOperationError: If execution fails
        """
        if not self.enable_libvirt:
            # 模拟模式
            logger.info(f"[Mock SSH] Executing on {host}: {command}")
            
            # 模拟延迟
            await asyncio.sleep(0.1)
            
            # 模拟成功响应
            return {
                "exit_code": 0,
                "stdout": f"[Mock] Command executed: {command}",
                "stderr": ""
            }
        
        # 真实模式 - 使用 asyncssh
        try:
            import asyncssh
            
            async with asyncssh.connect(
                host,
                username=self.user,
                client_keys=[self.key_path],
                known_hosts=None,  # 生产环境应使用 proper host key verification
                connect_timeout=self.connect_timeout
            ) as conn:
                result = await asyncio.wait_for(
                    conn.run(command, check=False),
                    timeout=timeout
                )
                
                return {
                    "exit_code": result.exit_status,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
        except asyncio.TimeoutError:
            raise VMOperationError("ssh_execute", f"Command timeout after {timeout}s")
        except Exception as e:
            logger.error(f"SSH command failed on {host}: {e}")
            raise VMOperationError("ssh_execute", str(e))
    
    async def deploy_openclaw(
        self,
        host: str,
        ssh_key: Optional[str] = None,
        config: Optional[DeployConfig] = None
    ) -> Dict[str, Any]:
        """
        Deploy OpenClaw to a VM.
        
        Args:
            host: VM IP address
            ssh_key: SSH private key (optional, uses default if not provided)
            config: Deployment configuration
            
        Returns:
            Deployment result with status and logs
            
        Raises:
            VMOperationError: If deployment fails
        """
        config = config or DeployConfig()
        
        logger.info(f"Starting OpenClaw deployment to {host}")
        
        deployment_log = []
        
        try:
            # 步骤 1: 检查连接
            logger.info(f"[1/6] Testing SSH connection to {host}")
            result = await self._execute_ssh_command(host, "echo 'SSH connection successful'")
            deployment_log.append(f"SSH connection: OK")
            
            # 步骤 2: 更新系统
            logger.info(f"[2/6] Updating system packages")
            result = await self._execute_ssh_command(
                host,
                "apt-get update && apt-get upgrade -y",
                timeout=300
            )
            if result["exit_code"] != 0:
                logger.warning(f"System update had issues: {result['stderr']}")
            deployment_log.append(f"System update: OK")
            
            # 步骤 3: 安装依赖
            logger.info(f"[3/6] Installing dependencies")
            install_cmd = "apt-get install -y curl wget git nodejs npm"
            if config.install_docker:
                install_cmd += " docker.io docker-compose"
            
            result = await self._execute_ssh_command(host, install_cmd, timeout=300)
            if result["exit_code"] != 0:
                raise VMOperationError("deploy", f"Failed to install dependencies: {result['stderr']}")
            deployment_log.append(f"Dependencies installed: OK")
            
            # 步骤 4: 安装 OpenClaw
            logger.info(f"[4/6] Installing OpenClaw (version: {config.openclaw_version})")
            install_openclaw_cmd = f"npm install -g openclaw@{config.openclaw_version}"
            if config.openclaw_version == "latest":
                install_openclaw_cmd = "npm install -g openclaw"
            
            result = await self._execute_ssh_command(host, install_openclaw_cmd, timeout=300)
            if result["exit_code"] != 0:
                raise VMOperationError("deploy", f"Failed to install OpenClaw: {result['stderr']}")
            deployment_log.append(f"OpenClaw installed: OK")
            
            # 步骤 5: 初始化 OpenClaw
            logger.info(f"[5/6] Initializing OpenClaw")
            result = await self._execute_ssh_command(host, "openclaw init --non-interactive", timeout=60)
            if result["exit_code"] != 0:
                raise VMOperationError("deploy", f"Failed to initialize OpenClaw: {result['stderr']}")
            deployment_log.append(f"OpenClaw initialized: OK")
            
            # 步骤 6: 配置并启动服务
            logger.info(f"[6/6] Configuring and starting OpenClaw Gateway")
            
            # 配置 agents
            for agent_config in config.agents:
                agent_name = agent_config.get("name", "default")
                logger.info(f"Configuring agent: {agent_name}")
                
                import json
                config_json = json.dumps(agent_config)
                result = await self._execute_ssh_command(
                    host,
                    f"openclaw agent create --config '{config_json}'",
                    timeout=60
                )
                if result["exit_code"] != 0:
                    logger.warning(f"Agent creation failed: {result['stderr']}")
            
            # 执行自定义脚本
            for script in config.custom_scripts:
                logger.info(f"Executing custom script: {script[:50]}...")
                result = await self._execute_ssh_command(host, script, timeout=120)
                if result["exit_code"] != 0:
                    logger.warning(f"Custom script failed: {result['stderr']}")
            
            # 启动服务
            result = await self._execute_ssh_command(
                host,
                "systemctl enable openclaw-gateway && systemctl start openclaw-gateway",
                timeout=60
            )
            if result["exit_code"] != 0:
                raise VMOperationError("deploy", f"Failed to start OpenClaw service: {result['stderr']}")
            
            # 验证服务状态
            await asyncio.sleep(5)  # 等待服务启动
            result = await self._execute_ssh_command(host, "systemctl is-active openclaw-gateway")
            if result["exit_code"] != 0 or "active" not in result["stdout"]:
                raise VMOperationError("deploy", "OpenClaw service failed to start")
            
            deployment_log.append(f"OpenClaw Gateway started: OK")
            
            logger.info(f"OpenClaw deployment completed successfully on {host}")
            
            return {
                "status": "success",
                "host": host,
                "openclaw_version": config.openclaw_version,
                "agents_configured": len(config.agents),
                "logs": deployment_log
            }
            
        except Exception as e:
            logger.error(f"OpenClaw deployment failed on {host}: {e}")
            deployment_log.append(f"ERROR: {str(e)}")
            
            return {
                "status": "failed",
                "host": host,
                "error": str(e),
                "logs": deployment_log
            }
    
    async def configure_channel(
        self,
        host: str,
        channel_type: str,
        channel_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Configure a channel on the VM.
        
        Args:
            host: VM IP address
            channel_type: Type of channel (feishu, telegram, etc.)
            channel_config: Channel configuration
            
        Returns:
            Configuration result
            
        Raises:
            VMOperationError: If configuration fails
        """
        try:
            import json
            config_json = json.dumps(channel_config)
            
            result = await self._execute_ssh_command(
                host,
                f"openclaw config set channels.{channel_type} '{config_json}'",
                timeout=30
            )
            
            if result["exit_code"] != 0:
                raise VMOperationError("configure_channel", result["stderr"])
            
            # 重启服务
            result = await self._execute_ssh_command(host, "systemctl restart openclaw-gateway")
            if result["exit_code"] != 0:
                raise VMOperationError("configure_channel", "Failed to restart service")
            
            logger.info(f"Channel {channel_type} configured successfully on {host}")
            
            return {
                "status": "success",
                "channel_type": channel_type,
                "message": f"Channel {channel_type} configured and service restarted"
            }
        except Exception as e:
            logger.error(f"Failed to configure channel on {host}: {e}")
            raise VMOperationError("configure_channel", str(e))
    
    async def get_agent_status(self, host: str, agent_id: str) -> Dict[str, Any]:
        """
        Get agent status from VM.
        
        Args:
            host: VM IP address
            agent_id: Agent ID
            
        Returns:
            Agent status information
            
        Raises:
            VMOperationError: If status retrieval fails
        """
        try:
            result = await self._execute_ssh_command(
                host,
                f"openclaw agent status {agent_id}",
                timeout=30
            )
            
            if result["exit_code"] != 0:
                raise VMOperationError("agent_status", result["stderr"])
            
            import json
            return json.loads(result["stdout"])
        except Exception as e:
            logger.error(f"Failed to get agent status from {host}: {e}")
            raise VMOperationError("agent_status", str(e))
    
    async def check_openclaw_health(self, host: str) -> Dict[str, Any]:
        """
        Check OpenClaw health status on VM.
        
        Args:
            host: VM IP address
            
        Returns:
            Health check result
        """
        try:
            # 检查服务状态
            result = await self._execute_ssh_command(
                host,
                "systemctl is-active openclaw-gateway && openclaw --version",
                timeout=30
            )
            
            is_healthy = result["exit_code"] == 0 and "active" in result["stdout"]
            
            return {
                "host": host,
                "is_healthy": is_healthy,
                "service_status": "active" if is_healthy else "inactive",
                "version": result["stdout"].split("\n")[1] if len(result["stdout"].split("\n")) > 1 else "unknown"
            }
        except Exception as e:
            logger.error(f"Health check failed on {host}: {e}")
            return {
                "host": host,
                "is_healthy": False,
                "error": str(e)
            }


# Global instance
ssh_deployer = SSHDeployer()
