"""
主密钥管理模块
处理主密钥的生成、加密和恢复
"""

import os
import secrets
import hashlib
from typing import Tuple, Optional
from dataclasses import dataclass

from crypto.aes import AESCipher
from crypto.rsa import RSACipher
from crypto.kdf import KeyDerivation


@dataclass
class MasterKeyBundle:
    """主密钥包"""
    master_key: bytes                    # 明文主密钥（仅在内存中）
    encrypted_master_key: bytes          # 密码加密的主密钥
    master_key_salt: bytes               # 密码加密盐值
    recovery_key_encrypted: bytes        # 恢复密钥加密的主密钥
    recovery_key_salt: bytes             # 恢复密钥盐值
    recovery_key_hash: bytes             # 恢复密钥哈希


class MasterKeyManager:
    """主密钥管理器"""
    
    MASTER_KEY_SIZE = 32  # 256 bits
    
    @staticmethod
    def generate_master_key() -> bytes:
        """生成随机主密钥"""
        return os.urandom(MasterKeyManager.MASTER_KEY_SIZE)
    
    @staticmethod
    def generate_recovery_key() -> str:
        """
        生成恢复密钥
        
        Returns:
            24 个字符的恢复密钥（Base32 编码，易于手动输入）
        """
        # 生成 120 bits 的随机数据
        random_bytes = os.urandom(15)
        # Base32 编码（不含填充）
        import base64
        recovery_key = base64.b32encode(random_bytes).decode('ascii').rstrip('=')
        # 分组显示
        return '-'.join([recovery_key[i:i+4] for i in range(0, len(recovery_key), 4)])
    
    @classmethod
    def create_master_key_bundle(cls, password: str) -> Tuple[MasterKeyBundle, str]:
        """
        创建主密钥包（注册时调用）
        
        Args:
            password: 用户密码
            
        Returns:
            (主密钥包, 恢复密钥明文)
        """
        # 生成主密钥
        master_key = cls.generate_master_key()
        
        # 使用密码加密主密钥
        password_salt = KeyDerivation.generate_salt()
        password_derived = KeyDerivation.derive_key(password, password_salt)
        cipher = AESCipher(password_derived)
        encrypted_master_key, iv = cipher.encrypt_cbc(master_key)
        encrypted_master_key = iv + encrypted_master_key  # IV 放在密文前
        
        # 生成恢复密钥并加密主密钥
        recovery_key = cls.generate_recovery_key()
        recovery_key_normalized = recovery_key.replace('-', '').upper()
        recovery_salt = KeyDerivation.generate_salt()
        recovery_derived = KeyDerivation.derive_key(recovery_key_normalized, recovery_salt)
        recovery_cipher = AESCipher(recovery_derived)
        recovery_encrypted, recovery_iv = recovery_cipher.encrypt_cbc(master_key)
        recovery_encrypted = recovery_iv + recovery_encrypted
        
        # 恢复密钥哈希（用于验证）
        recovery_hash = hashlib.sha256(recovery_key_normalized.encode()).digest()
        
        bundle = MasterKeyBundle(
            master_key=master_key,
            encrypted_master_key=encrypted_master_key,
            master_key_salt=password_salt,
            recovery_key_encrypted=recovery_encrypted,
            recovery_key_salt=recovery_salt,
            recovery_key_hash=recovery_hash
        )
        
        return bundle, recovery_key
    
    @classmethod
    def decrypt_with_password(cls, encrypted_master_key: bytes, 
                               salt: bytes, password: str) -> Optional[bytes]:
        """
        使用密码解密主密钥
        
        Args:
            encrypted_master_key: 加密的主密钥（IV + 密文）
            salt: 密码盐值
            password: 用户密码
            
        Returns:
            主密钥明文，失败返回 None
        """
        try:
            password_derived = KeyDerivation.derive_key(password, salt)
            cipher = AESCipher(password_derived)
            iv = encrypted_master_key[:16]
            ciphertext = encrypted_master_key[16:]
            return cipher.decrypt_cbc(ciphertext, iv)
        except Exception:
            return None
    
    @classmethod
    def decrypt_with_recovery(cls, recovery_encrypted: bytes,
                               salt: bytes, recovery_key: str) -> Optional[bytes]:
        """
        使用恢复密钥解密主密钥
        
        Args:
            recovery_encrypted: 加密的主密钥（IV + 密文）
            salt: 恢复盐值
            recovery_key: 恢复密钥
            
        Returns:
            主密钥明文，失败返回 None
        """
        try:
            recovery_normalized = recovery_key.replace('-', '').replace(' ', '').upper()
            recovery_derived = KeyDerivation.derive_key(recovery_normalized, salt)
            cipher = AESCipher(recovery_derived)
            iv = recovery_encrypted[:16]
            ciphertext = recovery_encrypted[16:]
            return cipher.decrypt_cbc(ciphertext, iv)
        except Exception:
            return None
    
    @classmethod
    def reencrypt_with_new_password(cls, master_key: bytes, 
                                     new_password: str) -> Tuple[bytes, bytes]:
        """
        使用新密码重新加密主密钥
        
        Args:
            master_key: 主密钥明文
            new_password: 新密码
            
        Returns:
            (新加密的主密钥, 新盐值)
        """
        new_salt = KeyDerivation.generate_salt()
        password_derived = KeyDerivation.derive_key(new_password, new_salt)
        cipher = AESCipher(password_derived)
        encrypted, iv = cipher.encrypt_cbc(master_key)
        return iv + encrypted, new_salt
    
    @classmethod
    def verify_recovery_key(cls, recovery_key: str, stored_hash: bytes) -> bool:
        """
        验证恢复密钥
        
        Args:
            recovery_key: 用户输入的恢复密钥
            stored_hash: 存储的恢复密钥哈希
            
        Returns:
            是否匹配
        """
        recovery_normalized = recovery_key.replace('-', '').replace(' ', '').upper()
        computed_hash = hashlib.sha256(recovery_normalized.encode()).digest()
        return secrets.compare_digest(computed_hash, stored_hash)


class UserKeyManager:
    """用户密钥管理器"""
    
    @staticmethod
    def generate_user_keypair(master_key: bytes) -> Tuple[bytes, bytes, bytes, bytes]:
        """
        生成用户 RSA 密钥对
        
        Args:
            master_key: 主密钥（用于加密私钥）
            
        Returns:
            (公钥, 加密的私钥, 私钥盐值, 私钥IV)
        """
        # 生成 RSA 密钥对
        private_key, public_key = RSACipher.generate_keypair()
        
        # 使用主密钥加密私钥
        cipher = AESCipher(master_key)
        encrypted_private_key, iv = cipher.encrypt_cbc(private_key)
        
        return public_key, iv + encrypted_private_key, b'', iv
    
    @staticmethod
    def decrypt_private_key(encrypted_private_key: bytes, 
                            master_key: bytes) -> Optional[bytes]:
        """
        解密用户私钥
        
        Args:
            encrypted_private_key: 加密的私钥（IV + 密文）
            master_key: 主密钥
            
        Returns:
            私钥明文
        """
        try:
            cipher = AESCipher(master_key)
            iv = encrypted_private_key[:16]
            ciphertext = encrypted_private_key[16:]
            return cipher.decrypt_cbc(ciphertext, iv)
        except Exception:
            return None
