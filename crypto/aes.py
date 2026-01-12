"""
AES-256 对称加密模块
支持 CBC 和 CTR 模式
"""

import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


class AESCipher:
    """AES-256 加密器"""
    
    KEY_SIZE = 32  # 256 bits
    BLOCK_SIZE = 16  # 128 bits
    
    def __init__(self, key: bytes = None):
        """
        初始化 AES 加密器
        
        Args:
            key: 32 字节密钥，如果为 None 则自动生成
        """
        if key is None:
            key = self.generate_key()
        if len(key) != self.KEY_SIZE:
            raise ValueError(f"密钥长度必须为 {self.KEY_SIZE} 字节")
        self.key = key
    
    @staticmethod
    def generate_key() -> bytes:
        """生成随机 256 位密钥"""
        return os.urandom(32)
    
    @staticmethod
    def generate_iv() -> bytes:
        """生成随机初始化向量"""
        return os.urandom(16)
    
    def encrypt_cbc(self, plaintext: bytes, iv: bytes = None) -> tuple[bytes, bytes]:
        """
        使用 CBC 模式加密
        
        Args:
            plaintext: 明文数据
            iv: 初始化向量，如果为 None 则自动生成
            
        Returns:
            (密文, IV) 元组
        """
        if iv is None:
            iv = self.generate_iv()
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(plaintext, self.BLOCK_SIZE))
        return ciphertext, iv
    
    def decrypt_cbc(self, ciphertext: bytes, iv: bytes) -> bytes:
        """
        使用 CBC 模式解密
        
        Args:
            ciphertext: 密文数据
            iv: 初始化向量
            
        Returns:
            明文数据
        """
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(ciphertext), self.BLOCK_SIZE)
        return plaintext
    
    def encrypt_ctr(self, plaintext: bytes, nonce: bytes = None) -> tuple[bytes, bytes]:
        """
        使用 CTR 模式加密（适用于流式加密）
        
        Args:
            plaintext: 明文数据
            nonce: 8 字节 nonce，如果为 None 则自动生成
            
        Returns:
            (密文, nonce) 元组
        """
        if nonce is None:
            nonce = os.urandom(8)
        cipher = AES.new(self.key, AES.MODE_CTR, nonce=nonce)
        ciphertext = cipher.encrypt(plaintext)
        return ciphertext, nonce
    
    def decrypt_ctr(self, ciphertext: bytes, nonce: bytes) -> bytes:
        """
        使用 CTR 模式解密
        
        Args:
            ciphertext: 密文数据
            nonce: 8 字节 nonce
            
        Returns:
            明文数据
        """
        cipher = AES.new(self.key, AES.MODE_CTR, nonce=nonce)
        plaintext = cipher.decrypt(ciphertext)
        return plaintext
    
    def encrypt_gcm(self, plaintext: bytes, aad: bytes = None) -> tuple[bytes, bytes, bytes]:
        """
        使用 GCM 模式加密（认证加密）
        
        Args:
            plaintext: 明文数据
            aad: 附加认证数据（可选）
            
        Returns:
            (密文, nonce, tag) 元组
        """
        cipher = AES.new(self.key, AES.MODE_GCM)
        if aad:
            cipher.update(aad)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        return ciphertext, cipher.nonce, tag
    
    def decrypt_gcm(self, ciphertext: bytes, nonce: bytes, tag: bytes, aad: bytes = None) -> bytes:
        """
        使用 GCM 模式解密
        
        Args:
            ciphertext: 密文数据
            nonce: nonce
            tag: 认证标签
            aad: 附加认证数据（可选）
            
        Returns:
            明文数据
            
        Raises:
            ValueError: 如果认证失败
        """
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        if aad:
            cipher.update(aad)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        return plaintext
