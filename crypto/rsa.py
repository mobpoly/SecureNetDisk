"""
RSA-2048 非对称加密模块
支持加解密和数字签名
"""

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256


class RSACipher:
    """RSA-2048 加密器"""
    
    KEY_SIZE = 2048
    
    def __init__(self, private_key: bytes = None, public_key: bytes = None):
        """
        初始化 RSA 加密器
        
        Args:
            private_key: PEM 格式私钥
            public_key: PEM 格式公钥
        """
        self._private_key = None
        self._public_key = None
        
        if private_key:
            self._private_key = RSA.import_key(private_key)
            self._public_key = self._private_key.publickey()
        elif public_key:
            self._public_key = RSA.import_key(public_key)
    
    @classmethod
    def generate_keypair(cls) -> tuple[bytes, bytes]:
        """
        生成 RSA 密钥对
        
        Returns:
            (私钥 PEM, 公钥 PEM) 元组
        """
        key = RSA.generate(cls.KEY_SIZE)
        private_key = key.export_key('PEM')
        public_key = key.publickey().export_key('PEM')
        return private_key, public_key
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """
        使用公钥加密
        
        Args:
            plaintext: 明文数据（最大 190 字节）
            
        Returns:
            密文数据
        """
        if self._public_key is None:
            raise ValueError("未设置公钥")
        cipher = PKCS1_OAEP.new(self._public_key)
        return cipher.encrypt(plaintext)
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        使用私钥解密
        
        Args:
            ciphertext: 密文数据
            
        Returns:
            明文数据
        """
        if self._private_key is None:
            raise ValueError("未设置私钥")
        cipher = PKCS1_OAEP.new(self._private_key)
        return cipher.decrypt(ciphertext)
    
    def sign(self, message: bytes) -> bytes:
        """
        使用私钥签名
        
        Args:
            message: 待签名消息
            
        Returns:
            签名数据
        """
        if self._private_key is None:
            raise ValueError("未设置私钥")
        h = SHA256.new(message)
        signature = pkcs1_15.new(self._private_key).sign(h)
        return signature
    
    def verify(self, message: bytes, signature: bytes) -> bool:
        """
        使用公钥验证签名
        
        Args:
            message: 原始消息
            signature: 签名数据
            
        Returns:
            验证是否通过
        """
        if self._public_key is None:
            raise ValueError("未设置公钥")
        h = SHA256.new(message)
        try:
            pkcs1_15.new(self._public_key).verify(h, signature)
            return True
        except (ValueError, TypeError):
            return False
    
    @property
    def public_key_bytes(self) -> bytes:
        """获取公钥 PEM"""
        if self._public_key:
            return self._public_key.export_key('PEM')
        return None
    
    @property
    def private_key_bytes(self) -> bytes:
        """获取私钥 PEM"""
        if self._private_key:
            return self._private_key.export_key('PEM')
        return None
