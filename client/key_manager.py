"""
密钥管理模块
管理用户的本地密钥
"""

import os
from typing import Optional, Dict
from dataclasses import dataclass

from crypto.aes import AESCipher
from crypto.rsa import RSACipher
from crypto.kdf import KeyDerivation
from auth.master_key import MasterKeyManager, UserKeyManager


@dataclass
class UserKeys:
    """用户密钥集合"""
    user_id: int
    username: str
    email: str
    master_key: bytes          # 主密钥（明文，仅在内存中）
    private_key: bytes         # RSA 私钥（明文，仅在内存中）
    public_key: bytes          # RSA 公钥


class KeyManager:
    """客户端密钥管理器"""
    
    def __init__(self):
        """初始化密钥管理器"""
        self.user_keys: Optional[UserKeys] = None
        self.group_keys: Dict[int, bytes] = {}  # group_id -> group_key
    
    @property
    def is_unlocked(self) -> bool:
        """密钥是否已解锁"""
        return self.user_keys is not None
    
    def prepare_registration(self, password: str) -> dict:
        """
        准备注册数据
        
        Args:
            password: 用户密码
            
        Returns:
            注册所需的密钥数据
        """
        # 创建主密钥包
        bundle, recovery_key = MasterKeyManager.create_master_key_bundle(password)
        
        # 生成 RSA 密钥对
        public_key, encrypted_private_key, _, _ = UserKeyManager.generate_user_keypair(
            bundle.master_key
        )
        
        # 计算密码哈希（用于服务端验证）
        # 先用 SHA-256 预哈希，再用 bcrypt 哈希
        from auth.password import PasswordManager
        password_prehash = PasswordManager.prehash_password(password)
        password_hash = PasswordManager.hash_password(password_prehash)
        
        return {
            'password_hash': password_hash.hex(),
            'public_key': public_key.hex(),
            'encrypted_private_key': encrypted_private_key.hex(),
            'encrypted_master_key': bundle.encrypted_master_key.hex(),
            'master_key_salt': bundle.master_key_salt.hex(),
            'recovery_key_encrypted': bundle.recovery_key_encrypted.hex(),
            'recovery_key_salt': bundle.recovery_key_salt.hex(),
            'recovery_key_hash': bundle.recovery_key_hash.hex(),
            'recovery_key': recovery_key,  # 需要展示给用户保存
            'master_key': bundle.master_key  # 临时保存
        }
    
    def unlock_with_password(self, password: str, user_data: dict) -> bool:
        """
        使用密码解锁密钥
        
        Args:
            password: 用户密码
            user_data: 从服务器获取的用户数据
            
        Returns:
            是否成功解锁
        """
        try:
            encrypted_master_key = bytes.fromhex(user_data['encrypted_master_key'])
            master_key_salt = bytes.fromhex(user_data['master_key_salt'])
            
            # 解密主密钥
            master_key = MasterKeyManager.decrypt_with_password(
                encrypted_master_key, master_key_salt, password
            )
            
            if not master_key:
                return False
            
            # 解密私钥
            encrypted_private_key = bytes.fromhex(user_data['encrypted_private_key'])
            private_key = UserKeyManager.decrypt_private_key(
                encrypted_private_key, master_key
            )
            
            if not private_key:
                return False
            
            # 保存密钥
            self.user_keys = UserKeys(
                user_id=user_data['user_id'],
                username=user_data['username'],
                email=user_data['email'],
                master_key=master_key,
                private_key=private_key,
                public_key=bytes.fromhex(user_data['public_key'])
            )
            
            return True
        except Exception as e:
            print(f"[KeyManager] 解锁失败: {e}")
            return False
    
    def unlock_with_recovery(self, recovery_key: str, user_data: dict) -> bool:
        """
        使用恢复密钥解锁密钥
        
        Args:
            recovery_key: 恢复密钥
            user_data: 从服务器获取的用户数据
            
        Returns:
            是否成功解锁
        """
        try:
            recovery_encrypted = bytes.fromhex(user_data['recovery_key_encrypted'])
            recovery_salt = bytes.fromhex(user_data['recovery_key_salt'])
            
            # 解密主密钥
            master_key = MasterKeyManager.decrypt_with_recovery(
                recovery_encrypted, recovery_salt, recovery_key
            )
            
            if not master_key:
                return False
            
            # 解密私钥
            encrypted_private_key = bytes.fromhex(user_data['encrypted_private_key'])
            private_key = UserKeyManager.decrypt_private_key(
                encrypted_private_key, master_key
            )
            
            if not private_key:
                return False
            
            # 保存密钥
            self.user_keys = UserKeys(
                user_id=user_data['user_id'],
                username=user_data['username'],
                email=user_data['email'],
                master_key=master_key,
                private_key=private_key,
                public_key=bytes.fromhex(user_data['public_key'])
            )
            
            return True
        except Exception as e:
            print(f"[KeyManager] 恢复解锁失败: {e}")
            return False
    
    def prepare_password_reset(self, new_password: str) -> dict:
        """
        准备密码重置数据
        
        Args:
            new_password: 新密码
            
        Returns:
            密码重置所需的数据
        """
        if not self.user_keys:
            raise ValueError("密钥未解锁")
        
        # 使用新密码重新加密主密钥
        new_encrypted, new_salt = MasterKeyManager.reencrypt_with_new_password(
            self.user_keys.master_key, new_password
        )
        
        # 计算新密码哈希（先 SHA-256 预哈希，再 bcrypt）
        from auth.password import PasswordManager
        new_prehash = PasswordManager.prehash_password(new_password)
        new_hash = PasswordManager.hash_password(new_prehash)
        
        return {
            'new_password_hash': new_hash.hex(),
            'new_encrypted_master_key': new_encrypted.hex(),
            'new_master_key_salt': new_salt.hex()
        }
    
    def lock(self):
        """锁定密钥（清除内存）"""
        self.user_keys = None
        self.group_keys.clear()
    
    def encrypt_file_key(self, file_key: bytes) -> bytes:
        """使用主密钥加密文件密钥"""
        if not self.user_keys:
            raise ValueError("密钥未解锁")
        
        cipher = AESCipher(self.user_keys.master_key)
        encrypted, iv = cipher.encrypt_cbc(file_key)
        return iv + encrypted
    
    def decrypt_file_key(self, encrypted_file_key: bytes) -> bytes:
        """解密文件密钥"""
        if not self.user_keys:
            raise ValueError("密钥未解锁")
        
        iv = encrypted_file_key[:16]
        ciphertext = encrypted_file_key[16:]
        
        cipher = AESCipher(self.user_keys.master_key)
        return cipher.decrypt_cbc(ciphertext, iv)
    
    def generate_group_key(self) -> bytes:
        """生成群组密钥"""
        return os.urandom(32)
    
    def encrypt_for_user(self, data: bytes, user_public_key: bytes) -> bytes:
        """
        使用用户公钥加密数据
        
        Args:
            data: 要加密的数据
            user_public_key: 目标用户的公钥
            
        Returns:
            加密后的数据
        """
        rsa = RSACipher(public_key=user_public_key)
        return rsa.encrypt(data)
    
    def decrypt_for_me(self, encrypted_data: bytes) -> bytes:
        """
        使用自己的私钥解密数据
        
        Args:
            encrypted_data: 加密的数据
            
        Returns:
            解密后的数据
        """
        if not self.user_keys:
            raise ValueError("密钥未解锁")
        
        rsa = RSACipher(private_key=self.user_keys.private_key)
        return rsa.decrypt(encrypted_data)
    
    def set_group_key(self, group_id: int, group_key: bytes):
        """设置群组密钥"""
        self.group_keys[group_id] = group_key
    
    def get_group_key(self, group_id: int) -> Optional[bytes]:
        """获取群组密钥"""
        return self.group_keys.get(group_id)
    
    def encrypt_with_group_key(self, group_id: int, data: bytes) -> bytes:
        """使用群组密钥加密"""
        group_key = self.group_keys.get(group_id)
        if not group_key:
            raise ValueError("群组密钥不存在")
        
        cipher = AESCipher(group_key)
        encrypted, iv = cipher.encrypt_cbc(data)
        return iv + encrypted
    
    def decrypt_with_group_key(self, group_id: int, encrypted_data: bytes) -> bytes:
        """使用群组密钥解密"""
        group_key = self.group_keys.get(group_id)
        if not group_key:
            raise ValueError("群组密钥不存在")
        
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        cipher = AESCipher(group_key)
        return cipher.decrypt_cbc(ciphertext, iv)
