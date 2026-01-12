"""
服务器配置
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ServerConfig:
    """服务器配置"""
    
    # 网络配置
    host: str = "0.0.0.0"
    port: int = 9000
    
    # 存储配置
    base_path: Path = field(default_factory=lambda: Path("./storage"))
    database_path: Path = field(default_factory=lambda: Path("./storage/secure_disk.db"))
    
    # 服务器密钥路径
    server_private_key_path: Path = field(default_factory=lambda: Path("./storage/server_private.pem"))
    server_public_key_path: Path = field(default_factory=lambda: Path("./storage/server_public.pem"))
    
    # 会话配置
    max_connections: int = 1000
    session_timeout: int = 3600  # 秒
    
    # Email 配置
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    
    # 文件配置
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    chunk_size: int = 64 * 1024  # 64KB
    
    def __post_init__(self):
        """初始化后处理"""
        # 转换为 Path 对象
        if isinstance(self.base_path, str):
            self.base_path = Path(self.base_path)
        if isinstance(self.database_path, str):
            self.database_path = Path(self.database_path)
        if isinstance(self.server_private_key_path, str):
            self.server_private_key_path = Path(self.server_private_key_path)
        if isinstance(self.server_public_key_path, str):
            self.server_public_key_path = Path(self.server_public_key_path)
        
        # 从环境变量读取配置
        self.host = os.environ.get('SERVER_HOST', self.host)
        self.port = int(os.environ.get('SERVER_PORT', self.port))
        self.smtp_host = os.environ.get('SMTP_HOST', self.smtp_host)
        self.smtp_port = int(os.environ.get('SMTP_PORT', self.smtp_port))
        self.smtp_user = os.environ.get('SMTP_USER', self.smtp_user)
        self.smtp_password = os.environ.get('SMTP_PASSWORD', self.smtp_password)
    
    def ensure_directories(self):
        """确保必要目录存在"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 用户文件存储目录
        (self.base_path / "users").mkdir(exist_ok=True)
        # 群组文件存储目录
        (self.base_path / "groups").mkdir(exist_ok=True)


# 默认配置
DEFAULT_CONFIG = ServerConfig()
