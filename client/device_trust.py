"""
设备信任管理模块
管理本地设备的信任状态和加密密钥存储
支持多用户：每个用户独立的信任状态
"""

import os
import json
import uuid
import sys
import time
from typing import Optional, Dict, List
from pathlib import Path
from dataclasses import dataclass, asdict

from crypto.aes import AESCipher

# Windows 平台使用 DPAPI 加密本地密钥
try:
    if sys.platform == 'win32':
        import win32crypt
    else:
        win32crypt = None
except ImportError:
    win32crypt = None


@dataclass
class UserDeviceInfo:
    """单个用户的设备信息"""
    username: str
    email: str
    trusted: bool
    device_key: str  # hex encoded (possibly DPAPI encrypted)
    encrypted_master_key: str  # hex encoded
    encrypted_private_key: str  # hex encoded
    public_key: str  # hex encoded
    trust_timestamp: float = 0.0  # 信任建立时间戳


class DeviceTrustManager:
    """设备信任管理器 - 支持多用户"""
    
    STORAGE_DIR = Path.home() / ".secure_netdisk"
    DEVICE_FILE = "device.json"
    TRUST_EXPIRY_DAYS = 7  # 信任有效期 7 天
    
    def __init__(self):
        self._ensure_storage_dir()
        self._device_id: Optional[str] = None
    
    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    @property
    def device_file_path(self) -> Path:
        return self.STORAGE_DIR / self.DEVICE_FILE
    
    def _load_all_data(self) -> dict:
        """加载所有设备数据"""
        try:
            if not self.device_file_path.exists():
                return {"device_id": str(uuid.uuid4()), "users": {}}
            
            with open(self.device_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 兼容旧格式（单用户）
            if "users" not in data:
                # 迁移旧数据
                if "username" in data:
                    old_user = UserDeviceInfo(
                        username=data.get("username", ""),
                        email=data.get("email", ""),
                        trusted=data.get("trusted", False),
                        device_key=data.get("device_key", ""),
                        encrypted_master_key=data.get("encrypted_master_key", ""),
                        encrypted_private_key=data.get("encrypted_private_key", ""),
                        public_key=data.get("public_key", "")
                    )
                    return {
                        "device_id": data.get("device_id", str(uuid.uuid4())),
                        "users": {old_user.email: asdict(old_user)}
                    }
                return {"device_id": str(uuid.uuid4()), "users": {}}
            
            return data
        except Exception as e:
            print(f"[DeviceTrust] 加载设备信息失败: {e}")
            return {"device_id": str(uuid.uuid4()), "users": {}}
    
    def _save_all_data(self, data: dict):
        """保存所有设备数据"""
        try:
            with open(self.device_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[DeviceTrust] 保存设备信息失败: {e}")
    
    def has_trusted_device(self, email: str = None) -> bool:
        """
        检查是否有信任的设备记录
        
        Args:
            email: 如果指定，检查该邮箱是否信任此设备
        """
        data = self._load_all_data()
        users = data.get("users", {})
        
        if email:
            user_info = users.get(email)
            return user_info is not None and user_info.get("trusted", False)
        
        # 检查是否有任何信任的用户
        return any(u.get("trusted", False) for u in users.values())
    
    def get_trusted_emails(self) -> List[str]:
        """获取所有信任此设备的用户邮箱列表"""
        data = self._load_all_data()
        users = data.get("users", {})
        return [email for email, info in users.items() if info.get("trusted", False)]
    
    def get_user_info_by_email(self, email: str) -> Optional[UserDeviceInfo]:
        """通过邮箱获取用户设备信息"""
        data = self._load_all_data()
        users = data.get("users", {})
        user_data = users.get(email)
        
        if user_data:
            return UserDeviceInfo(**user_data)
        return None
    
    def trust_device(self, username: str, email: str,
                     master_key: bytes, private_key: bytes, 
                     public_key: bytes) -> bool:
        """
        信任当前设备，保存加密的密钥
        
        Args:
            username: 用户名
            email: 用户邮箱（作为唯一标识）
            master_key: 主密钥明文
            private_key: RSA 私钥明文
            public_key: RSA 公钥
            
        Returns:
            是否成功
        """
        try:
            # 生成设备密钥
            device_key = os.urandom(32)
            
            # 使用设备密钥加密主密钥和私钥
            cipher = AESCipher(device_key)
            
            encrypted_master, iv1 = cipher.encrypt_cbc(master_key)
            encrypted_master = iv1 + encrypted_master
            
            encrypted_private, iv2 = cipher.encrypt_cbc(private_key)
            encrypted_private = iv2 + encrypted_private
            
            # 处理设备密钥的本地存储加密 (DPAPI)
            final_device_key = device_key
            if win32crypt:
                try:
                    # 使用 Windows DPAPI 加密，绑定到当前用户和机器
                    final_device_key = win32crypt.CryptProtectData(device_key, "SecureNetDisk Device Key", None, None, None, 0)
                except Exception as dpapi_err:
                    print(f"[DeviceTrust] DPAPI 加密失败，退回到普通存储: {dpapi_err}")

            # 创建用户信息
            user_info = UserDeviceInfo(
                username=username,
                email=email,
                trusted=True,
                device_key=final_device_key.hex(),
                encrypted_master_key=encrypted_master.hex(),
                encrypted_private_key=encrypted_private.hex(),
                public_key=public_key.hex(),
                trust_timestamp=time.time()
            )
            
            # 加载现有数据并添加/更新用户
            data = self._load_all_data()
            data["users"][email] = asdict(user_info)
            self._save_all_data(data)
            
            print(f"[DeviceTrust] 用户 {username} ({email}) 已信任此设备")
            return True
            
        except Exception as e:
            print(f"[DeviceTrust] 信任设备失败: {e}")
            return False
    
    def unlock_from_device(self, email: str) -> Optional[Dict]:
        """
        从设备加载并解密指定用户的密钥
        
        Args:
            email: 用户邮箱
            
        Returns:
            包含解密密钥的字典，失败返回 None
        """
        try:
            info = self.get_user_info_by_email(email)
            if not info or not info.trusted:
                return None
            
            # 校验过期时间 (7天)
            current_time = time.time()
            if info.trust_timestamp > 0: # 新版本有时间戳
                elapsed_days = (current_time - info.trust_timestamp) / (24 * 3600)
                if elapsed_days > self.TRUST_EXPIRY_DAYS:
                    print(f"[DeviceTrust] 用户 {email} 的设备信任已过期 ({elapsed_days:.1f} 天)")
                    self.mark_untrusted(email)
                    return None
            
            # 读取并解密设备密钥
            device_key_bytes = bytes.fromhex(info.device_key)
            
            if win32crypt:
                try:
                    # 尝试使用 DPAPI 解密
                    _, decrypted_device_key = win32crypt.CryptUnprotectData(device_key_bytes, None, None, None, 0)
                    device_key = decrypted_device_key
                except Exception:
                    # 如果解密失败，可能是旧版未加密的密钥，或者是被篡改/在不同机器上
                    # 这里尝试直接当做原始密钥使用（兼容旧数据）
                    device_key = device_key_bytes
            else:
                device_key = device_key_bytes

            cipher = AESCipher(device_key)
            
            # 解密主密钥
            encrypted_master = bytes.fromhex(info.encrypted_master_key)
            iv1 = encrypted_master[:16]
            master_key = cipher.decrypt_cbc(encrypted_master[16:], iv1)
            
            # 解密私钥
            encrypted_private = bytes.fromhex(info.encrypted_private_key)
            iv2 = encrypted_private[:16]
            private_key = cipher.decrypt_cbc(encrypted_private[16:], iv2)
            
            return {
                'username': info.username,
                'email': info.email,
                'master_key': master_key,
                'private_key': private_key,
                'public_key': bytes.fromhex(info.public_key)
            }
            
        except Exception as e:
            print(f"[DeviceTrust] 解锁失败: {e}")
            return None
    
    def clear_trust(self, email: str = None):
        """
        清除设备信任
        
        Args:
            email: 指定用户邮箱，None 则清除所有
        """
        try:
            if email:
                data = self._load_all_data()
                if email in data.get("users", {}):
                    del data["users"][email]
                    self._save_all_data(data)
                    print(f"[DeviceTrust] 用户 {email} 的设备信任已清除")
            else:
                if self.device_file_path.exists():
                    self.device_file_path.unlink()
                print("[DeviceTrust] 所有设备信任已清除")
        except Exception as e:
            print(f"[DeviceTrust] 清除信任失败: {e}")
    
    def mark_untrusted(self, email: str):
        """标记指定用户为不信任"""
        data = self._load_all_data()
        if email in data.get("users", {}):
            data["users"][email]["trusted"] = False
            self._save_all_data(data)
