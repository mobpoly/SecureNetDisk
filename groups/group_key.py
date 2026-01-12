"""
群组密钥管理模块
处理群组密钥的加密和分发
"""

import os
from typing import Dict, List, Optional, Tuple

from crypto.aes import AESCipher
from crypto.rsa import RSACipher


class GroupKeyManager:
    """群组密钥管理器"""
    
    def __init__(self, key_manager):
        """
        初始化群组密钥管理器
        
        Args:
            key_manager: 用户密钥管理器
        """
        self.key_manager = key_manager
    
    @staticmethod
    def generate_group_key() -> bytes:
        """生成群组密钥"""
        return os.urandom(32)
    
    def encrypt_group_key_for_member(self, group_key: bytes, 
                                      member_public_key: bytes) -> bytes:
        """
        为成员加密群组密钥
        
        Args:
            group_key: 群组密钥
            member_public_key: 成员公钥
            
        Returns:
            加密后的群组密钥
        """
        rsa = RSACipher(public_key=member_public_key)
        return rsa.encrypt(group_key)
    
    def decrypt_group_key(self, encrypted_group_key: bytes) -> bytes:
        """
        解密群组密钥
        
        Args:
            encrypted_group_key: 加密的群组密钥
            
        Returns:
            群组密钥
        """
        return self.key_manager.decrypt_for_me(encrypted_group_key)
    
    def encrypt_file_for_group(self, file_data: bytes, 
                               group_key: bytes) -> Tuple[bytes, bytes]:
        """
        为群组加密文件
        
        Args:
            file_data: 文件数据
            group_key: 群组密钥
            
        Returns:
            (加密数据, 加密的文件密钥)
        """
        # 生成文件密钥
        file_key = os.urandom(32)
        
        # 加密文件
        cipher = AESCipher(file_key)
        encrypted_data, iv = cipher.encrypt_cbc(file_data)
        
        # 使用群组密钥加密文件密钥
        group_cipher = AESCipher(group_key)
        encrypted_file_key, file_key_iv = group_cipher.encrypt_cbc(file_key)
        
        return iv + encrypted_data, file_key_iv + encrypted_file_key
    
    def decrypt_file_from_group(self, encrypted_data: bytes,
                                 encrypted_file_key: bytes,
                                 group_key: bytes) -> bytes:
        """
        解密群组文件
        
        Args:
            encrypted_data: 加密的文件数据
            encrypted_file_key: 加密的文件密钥
            group_key: 群组密钥
            
        Returns:
            解密后的文件数据
        """
        # 解密文件密钥
        file_key_iv = encrypted_file_key[:16]
        encrypted_key = encrypted_file_key[16:]
        
        group_cipher = AESCipher(group_key)
        file_key = group_cipher.decrypt_cbc(encrypted_key, file_key_iv)
        
        # 解密文件
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        file_cipher = AESCipher(file_key)
        return file_cipher.decrypt_cbc(ciphertext, iv)
    
    def prepare_key_distribution(self, group_key: bytes,
                                  member_public_keys: List[Dict]) -> Dict[int, bytes]:
        """
        准备密钥分发
        
        Args:
            group_key: 群组密钥
            member_public_keys: 成员公钥列表 [{'user_id': int, 'public_key': bytes}, ...]
            
        Returns:
            {user_id: encrypted_group_key, ...}
        """
        distribution = {}
        for member in member_public_keys:
            user_id = member['user_id']
            public_key = member['public_key']
            
            if isinstance(public_key, str):
                public_key = bytes.fromhex(public_key)
            
            encrypted = self.encrypt_group_key_for_member(group_key, public_key)
            distribution[user_id] = encrypted
        
        return distribution
