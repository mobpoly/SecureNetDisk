import configparser
import os
from dataclasses import dataclass, field
from typing import List

CONFIG_FILE = "client.ini"

@dataclass
class ClientConfig:
    """客户端配置管理，使用 configparser."""
    host: str = "localhost"
    port: int = 9000
    recent_hosts: List[str] = field(default_factory=list)
    last_username: str = ""

    def load(self):
        """从 client.ini 加载配置."""
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE, encoding="utf-8")

            # 网络设置
            if "Network" in config:
                self.host = config["Network"].get("host", "localhost")
                self.port = config["Network"].getint("port", 9000)

            # 历史记录设置
            if "History" in config:
                recent_str = config["History"].get("recent", "")
                if recent_str:
                    self.recent_hosts = [h.strip() for h in recent_str.split(",") if h.strip()]

            # 用户设置
            if "User" in config:
                self.last_username = config["User"].get("last_username", "")

    def save(self):
        """保存配置到 client.ini."""
        config = configparser.ConfigParser()

        config["Network"] = {
            "host": self.host,
            "port": str(self.port)
        }

        config["History"] = {
            "recent": ", ".join(self.recent_hosts)
        }

        config["User"] = {
            "last_username": self.last_username
        }

        with open(CONFIG_FILE, "w", encoding="utf-8") as configfile:
            config.write(configfile)

    def add_to_history(self, host: str, port: int):
        """将一个 host:port 添加到历史记录，仅保留最新的 5 个不重复条目."""
        entry = f"{host}:{port}"

        # 如果已存在则先移除，以便将其移动到顶部（最近使用）
        if entry in self.recent_hosts:
            self.recent_hosts.remove(entry)

        self.recent_hosts.insert(0, entry)

        # 仅保留前 5 个
        self.recent_hosts = self.recent_hosts[:5]
        self.save()

# 全局实例
config = ClientConfig()