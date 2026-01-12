"""
密钥派生函数模块
用于从密码派生加密密钥
"""

import os
import hashlib
import bcrypt
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256


class KeyDerivation:
    """密钥派生函数"""
    
    SALT_SIZE = 16
    KEY_SIZE = 32
    ITERATIONS = 100000  # PBKDF2 迭代次数
    
    @staticmethod
    def generate_salt() -> bytes:
        """生成随机盐值"""
        return os.urandom(KeyDerivation.SALT_SIZE)
    
    @staticmethod
    def derive_key(password: str, salt: bytes, key_size: int = 32) -> bytes:
        """
        从密码派生密钥（PBKDF2-HMAC-SHA256）
        
        Args:
            password: 用户密码
            salt: 盐值
            key_size: 输出密钥长度（字节）
            
        Returns:
            派生的密钥
        """
        return PBKDF2(
            password.encode('utf-8'),
            salt,
            dkLen=key_size,
            count=KeyDerivation.ITERATIONS,
            hmac_hash_module=SHA256
        )
    
    @staticmethod
    def derive_multiple_keys(password: str, salt: bytes, key_count: int = 2) -> list[bytes]:
        """
        从密码派生多个密钥
        
        Args:
            password: 用户密码
            salt: 盐值
            key_count: 要派生的密钥数量
            
        Returns:
            密钥列表
        """
        total_size = KeyDerivation.KEY_SIZE * key_count
        derived = PBKDF2(
            password.encode('utf-8'),
            salt,
            dkLen=total_size,
            count=KeyDerivation.ITERATIONS,
            hmac_hash_module=SHA256
        )
        return [
            derived[i * KeyDerivation.KEY_SIZE:(i + 1) * KeyDerivation.KEY_SIZE]
            for i in range(key_count)
        ]


class PasswordHash:
    """密码哈希（用于存储验证）"""
    
    @staticmethod
    def hash_password(password: str) -> bytes:
        """
        哈希密码（使用 bcrypt）
        
        Args:
            password: 明文密码
            
        Returns:
            密码哈希值
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    @staticmethod
    def verify_password(password: str, hashed: bytes) -> bool:
        """
        验证密码
        
        Args:
            password: 待验证的明文密码
            hashed: 存储的哈希值
            
        Returns:
            验证是否通过
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed)
        except Exception:
            return False
