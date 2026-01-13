import configparser
import os
from dataclasses import dataclass, field
from typing import List

CONFIG_FILE = "client.ini"

@dataclass
class ClientConfig:
    """Client configuration management using configparser."""
    host: str = "localhost"
    port: int = 9000
    recent_hosts: List[str] = field(default_factory=list)
    last_username: str = ""

    def load(self):
        """Load configuration from client.ini."""
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE, encoding="utf-8")
            
            # Network settings
            if "Network" in config:
                self.host = config["Network"].get("host", "localhost")
                self.port = config["Network"].getint("port", 9000)

            # History settings
            if "History" in config:
                recent_str = config["History"].get("recent", "")
                if recent_str:
                    self.recent_hosts = [h.strip() for h in recent_str.split(",") if h.strip()]

            # User settings
            if "User" in config:
                self.last_username = config["User"].get("last_username", "")

    def save(self):
        """Save configuration to client.ini."""
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
        """Add a host:port to history, keeping only the last 5 unique entries."""
        entry = f"{host}:{port}"
        
        # Remove if existing to move it to the top (most recent)
        if entry in self.recent_hosts:
            self.recent_hosts.remove(entry)
            
        self.recent_hosts.insert(0, entry)
        
        # Keep only top 5
        self.recent_hosts = self.recent_hosts[:5]
        self.save()

# Global instance
config = ClientConfig()
