"""
服务器配置
"""

import os
import configparser
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILE = "server.ini"

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
        """初始化后处理：加载外部配置文件"""
        self.load_from_file()
        
        # 环境变量仍具有最高优先级，方便容器化部署
        self.host = os.environ.get('SERVER_HOST', self.host)
        self.port = int(os.environ.get('SERVER_PORT', self.port))
        self.smtp_host = os.environ.get('SMTP_HOST', self.smtp_host)
        self.smtp_port = int(os.environ.get('SMTP_PORT', self.smtp_port))
        self.smtp_user = os.environ.get('SMTP_USER', self.smtp_user)
        self.smtp_password = os.environ.get('SMTP_PASSWORD', self.smtp_password)

        # 转换为 Path 对象
        self.base_path = Path(self.base_path)
        self.database_path = Path(self.database_path)
        self.server_private_key_path = Path(self.server_private_key_path)
        self.server_public_key_path = Path(self.server_public_key_path)

    def load_from_file(self):
        """从 server.ini 加载配置"""
        config = configparser.ConfigParser()
        if not os.path.exists(CONFIG_FILE):
            self.save_to_file()  # 如果不存在，则创建一个包含当前默认值的
            return

        config.read(CONFIG_FILE, encoding='utf-8')
        
        if "Network" in config:
            self.host = config["Network"].get("host", self.host)
            self.port = config["Network"].getint("port", self.port)
        
        if "Storage" in config:
            self.base_path = Path(config["Storage"].get("base_path", str(self.base_path)))
            self.database_path = Path(config["Storage"].get("database_path", str(self.database_path)))

        if "Security" in config:
            self.server_private_key_path = Path(config["Security"].get("private_key_path", str(self.server_private_key_path)))
            self.server_public_key_path = Path(config["Security"].get("public_key_path", str(self.server_public_key_path)))

        if "Email" in config:
            self.smtp_host = config["Email"].get("smtp_host", self.smtp_host)
            self.smtp_port = config["Email"].getint("smtp_port", self.smtp_port)
            self.smtp_user = config["Email"].get("smtp_user", self.smtp_user)
            self.smtp_password = config["Email"].get("smtp_password", self.smtp_password)

    def save_to_file(self):
        """将当前配置保存到 server.ini"""
        config = configparser.ConfigParser()
        config["Network"] = {
            "host": self.host,
            "port": str(self.port)
        }
        config["Storage"] = {
            "base_path": str(self.base_path),
            "database_path": str(self.database_path)
        }
        config["Security"] = {
            "private_key_path": str(self.server_private_key_path),
            "public_key_path": str(self.server_public_key_path)
        }
        config["Email"] = {
            "smtp_host": self.smtp_host,
            "smtp_port": str(self.smtp_port),
            "smtp_user": self.smtp_user,
            "smtp_password": self.smtp_password
        }
        
        try:
            with open(CONFIG_FILE, "w", encoding='utf-8') as configfile:
                config.write(configfile)
        except OSError as e:
            # 记录警告而不是让异常在初始化阶段传播
            print(f"警告: 无法写入配置文件 '{CONFIG_FILE}': {e}")
    
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
