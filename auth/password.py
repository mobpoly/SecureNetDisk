"""
密码管理模块
处理密码哈希和验证
"""

import bcrypt
import hashlib
import re
from typing import Tuple


class PasswordManager:
    """密码管理器"""
    
    MIN_PASSWORD_LENGTH = 8
    
    @staticmethod
    def prehash_password(password: str) -> str:
        """
        客户端预哈希密码（SHA-256，无盐，确定性）
        用于在传输前对密码进行哈希，避免明文传输
        
        Args:
            password: 明文密码
            
        Returns:
            SHA-256 哈希的十六进制字符串
        """
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    @staticmethod
    def hash_password(password: str) -> bytes:
        """
        哈希密码（服务端存储用）
        对已经过 SHA-256 预哈希的密码再进行 bcrypt 哈希
        
        Args:
            password: 预哈希后的密码（SHA-256 hex）
            
        Returns:
            bcrypt 哈希值
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
    
    @staticmethod
    def verify_password(prehashed: str, stored_hash: bytes) -> bool:
        """
        验证密码
        
        Args:
            prehashed: 预哈希后的密码（SHA-256 hex）
            stored_hash: 存储的 bcrypt 哈希值
            
        Returns:
            验证是否通过
        """
        try:
            return bcrypt.checkpw(prehashed.encode('utf-8'), stored_hash)
        except Exception:
            return False
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """
        验证密码强度
        
        Args:
            password: 待验证密码
            
        Returns:
            (是否有效, 错误消息)
        """
        if len(password) < PasswordManager.MIN_PASSWORD_LENGTH:
            return False, f"密码长度至少 {PasswordManager.MIN_PASSWORD_LENGTH} 位"
        
        # 检查是否包含数字
        if not re.search(r'\d', password):
            return False, "密码必须包含至少一个数字"
        
        # 检查是否包含字母
        if not re.search(r'[a-zA-Z]', password):
            return False, "密码必须包含至少一个字母"
        
        return True, ""
    
    @staticmethod
    def get_password_strength(password: str) -> int:
        """
        计算密码强度分数
        
        Args:
            password: 密码
            
        Returns:
            强度分数 0-100
        """
        score = 0
        
        # 长度分数
        if len(password) >= 8:
            score += 20
        if len(password) >= 12:
            score += 10
        if len(password) >= 16:
            score += 10
        
        # 包含小写字母
        if re.search(r'[a-z]', password):
            score += 15
        
        # 包含大写字母
        if re.search(r'[A-Z]', password):
            score += 15
        
        # 包含数字
        if re.search(r'\d', password):
            score += 15
        
        # 包含特殊字符
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 15
        
        return min(score, 100)
