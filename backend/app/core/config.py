"""
Application configuration management using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "OpenClaw VM Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 50
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Libvirt
    ENABLE_LIBVIRT: bool = False  # 模拟模式开关
    LIBVIRT_URI: str = "qemu:///system"
    LIBVIRT_POOL_NAME: str = "openclaw-vms"
    LIBVIRT_NETWORK_NAME: str = "openclaw-network"
    LIBVIRT_CONNECT_TIMEOUT: int = 10  # 秒

    # SSH
    SSH_PRIVATE_KEY_PATH: str = "/root/.ssh/id_rsa"
    SSH_USER: str = "root"
    SSH_CONNECT_TIMEOUT: int = 30  # 秒
    SSH_DEPLOY_TIMEOUT: int = 600  # 秒（10分钟）
    
    # VM Configuration
    VM_BASE_IMAGE_PATH: str = "/var/lib/libvirt/images/base.qcow2"
    VM_DEFAULT_CPU: int = 1
    VM_DEFAULT_MEMORY: int = 2048  # MB
    VM_DEFAULT_DISK: int = 20      # GB
    
    # Billing
    TOKEN_PRICE_PER_1K: float = 0.01
    DISK_PRICE_PER_GB: float = 0.5
    BACKUP_PRICE_PER_MONTH: float = 20.0
    
    # CORS
    CORS_ORIGINS: str = '["http://localhost:3000"]'
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Encryption
    ENCRYPTION_KEY: str = "change-this-32-bytes-encryption"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        try:
            return json.loads(self.CORS_ORIGINS)
        except:
            return ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
