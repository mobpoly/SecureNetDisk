"""
文件加密模块
处理文件的客户端加解密
"""

import os
from typing import Tuple, Optional
from pathlib import Path

from crypto.aes import AESCipher


class FileCrypto:
    """文件加密器"""
    
    CHUNK_SIZE = 64 * 1024  # 64KB
    
    @staticmethod
    def generate_file_key() -> bytes:
        """生成文件密钥"""
        return AESCipher.generate_key()
    
    @staticmethod
    def encrypt_file(file_path: Path, file_key: bytes) -> Tuple[bytes, int]:
        """
        加密文件
        
        Args:
            file_path: 文件路径
            file_key: 文件密钥
            
        Returns:
            (加密数据, 原始大小) 元组
        """
        with open(file_path, 'rb') as f:
            plaintext = f.read()
        
        cipher = AESCipher(file_key)
        ciphertext, iv = cipher.encrypt_cbc(plaintext)
        
        # IV + 密文
        encrypted_data = iv + ciphertext
        return encrypted_data, len(plaintext)
    
    @staticmethod
    def decrypt_file(encrypted_data: bytes, file_key: bytes) -> bytes:
        """
        解密文件
        
        Args:
            encrypted_data: 加密数据（IV + 密文）
            file_key: 文件密钥
            
        Returns:
            解密后的文件数据
        """
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        cipher = AESCipher(file_key)
        return cipher.decrypt_cbc(ciphertext, iv)
    
    @staticmethod
    def encrypt_file_streaming(file_path: Path, file_key: bytes):
        """
        流式加密文件（生成器）
        
        Args:
            file_path: 文件路径
            file_key: 文件密钥
            
        Yields:
            加密数据块
        """
        # 使用 CTR 模式支持流式加密
        cipher = AESCipher(file_key)
        nonce = os.urandom(8)
        
        # 首先 yield nonce
        yield nonce
        
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(FileCrypto.CHUNK_SIZE)
                if not chunk:
                    break
                
                encrypted_chunk, _ = cipher.encrypt_ctr(chunk, nonce)
                yield encrypted_chunk
    
    @staticmethod
    def encrypt_data(data: bytes, file_key: bytes) -> bytes:
        """
        加密内存中的数据
        
        Args:
            data: 明文数据
            file_key: 密钥
            
        Returns:
            加密数据（IV + 密文）
        """
        cipher = AESCipher(file_key)
        ciphertext, iv = cipher.encrypt_cbc(data)
        return iv + ciphertext
    
    @staticmethod
    def decrypt_data(encrypted_data: bytes, file_key: bytes) -> bytes:
        """
        解密内存中的数据
        
        Args:
            encrypted_data: 加密数据（IV + 密文）
            file_key: 密钥
            
        Returns:
            解密后的数据
        """
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        cipher = AESCipher(file_key)
        return cipher.decrypt_cbc(ciphertext, iv)


class FileKeyManager:
    """文件密钥管理器"""
    
    def __init__(self, master_key: bytes):
        """
        初始化文件密钥管理器
        
        Args:
            master_key: 用户主密钥
        """
        self.master_key = master_key
    
    def encrypt_file_key(self, file_key: bytes) -> bytes:
        """
        使用主密钥加密文件密钥
        
        Args:
            file_key: 文件密钥
            
        Returns:
            加密后的文件密钥
        """
        cipher = AESCipher(self.master_key)
        encrypted, iv = cipher.encrypt_cbc(file_key)
        return iv + encrypted
    
    def decrypt_file_key(self, encrypted_file_key: bytes) -> bytes:
        """
        解密文件密钥
        
        Args:
            encrypted_file_key: 加密的文件密钥
            
        Returns:
            文件密钥
        """
        iv = encrypted_file_key[:16]
        ciphertext = encrypted_file_key[16:]
        
        cipher = AESCipher(self.master_key)
        return cipher.decrypt_cbc(ciphertext, iv)
    
    def prepare_upload(self, file_path: Path) -> Tuple[bytes, bytes, bytes]:
        """
        准备文件上传
        
        Args:
            file_path: 文件路径
            
        Returns:
            (加密数据, 加密的文件密钥, 文件密钥) 元组
        """
        # 生成文件密钥
        file_key = FileCrypto.generate_file_key()
        
        # 加密文件
        encrypted_data, _ = FileCrypto.encrypt_file(file_path, file_key)
        
        # 加密文件密钥
        encrypted_file_key = self.encrypt_file_key(file_key)
        
        return encrypted_data, encrypted_file_key, file_key
    
    def decrypt_download(self, encrypted_data: bytes, 
                         encrypted_file_key: bytes) -> bytes:
        """
        解密下载的文件
        
        Args:
            encrypted_data: 加密的文件数据
            encrypted_file_key: 加密的文件密钥
            
        Returns:
            解密后的文件数据
        """
        # 解密文件密钥
        file_key = self.decrypt_file_key(encrypted_file_key)
        
        # 解密文件
        return FileCrypto.decrypt_file(encrypted_data, file_key)
