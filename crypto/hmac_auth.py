"""
HMAC-SHA256 消息认证模块
用于数据完整性校验和防篡改
"""

import hmac
import hashlib


class HMACAuth:
    """HMAC-SHA256 消息认证"""
    
    DIGEST_SIZE = 32  # SHA-256 产生 32 字节摘要
    
    def __init__(self, key: bytes):
        """
        初始化 HMAC 认证器
        
        Args:
            key: HMAC 密钥
        """
        if not key:
            raise ValueError("密钥不能为空")
        self.key = key
    
    def generate(self, message: bytes) -> bytes:
        """
        生成消息的 HMAC
        
        Args:
            message: 待认证消息
            
        Returns:
            32 字节 HMAC 值
        """
        return hmac.new(self.key, message, hashlib.sha256).digest()
    
    def verify(self, message: bytes, mac: bytes) -> bool:
        """
        验证消息的 HMAC
        
        Args:
            message: 原始消息
            mac: 待验证的 HMAC 值
            
        Returns:
            验证是否通过
        """
        expected = self.generate(message)
        return hmac.compare_digest(expected, mac)
    
    @staticmethod
    def quick_hmac(key: bytes, message: bytes) -> bytes:
        """
        快速生成 HMAC（静态方法）
        
        Args:
            key: HMAC 密钥
            message: 待认证消息
            
        Returns:
            32 字节 HMAC 值
        """
        return hmac.new(key, message, hashlib.sha256).digest()
    
    @staticmethod
    def quick_verify(key: bytes, message: bytes, mac: bytes) -> bool:
        """
        快速验证 HMAC（静态方法）
        
        Args:
            key: HMAC 密钥
            message: 原始消息
            mac: 待验证的 HMAC 值
            
        Returns:
            验证是否通过
        """
        expected = hmac.new(key, message, hashlib.sha256).digest()
        return hmac.compare_digest(expected, mac)
