"""
Diffie-Hellman 密钥交换模块
用于安全地协商会话密钥
"""

import os
import hashlib
from Crypto.PublicKey import DSA


class DHKeyExchange:
    """Diffie-Hellman 密钥交换"""
    
    # RFC 3526 MODP Group 14 (2048-bit)
    # 使用标准的 DH 参数以确保安全性
    PRIME = int(
        "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
        "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
        "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
        "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
        "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
        "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
        "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
        "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
        "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
        "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
        "15728E5A8AACAA68FFFFFFFFFFFFFFFF", 16
    )
    GENERATOR = 2
    
    def __init__(self):
        """初始化 DH 密钥交换"""
        self._private_key = None
        self._public_key = None
        self._shared_secret = None
    
    def generate_keypair(self) -> bytes:
        """
        生成 DH 密钥对
        
        Returns:
            公钥字节（用于发送给对方）
        """
        # 生成随机私钥 (256 bits)
        self._private_key = int.from_bytes(os.urandom(32), 'big')
        # 计算公钥: g^a mod p
        self._public_key = pow(self.GENERATOR, self._private_key, self.PRIME)
        return self._public_key.to_bytes(256, 'big')
    
    def compute_shared_secret(self, peer_public_key: bytes) -> bytes:
        """
        计算共享密钥
        
        Args:
            peer_public_key: 对方的公钥字节
            
        Returns:
            256 位共享密钥（SHA-256 哈希后）
        """
        if self._private_key is None:
            raise ValueError("请先调用 generate_keypair()")
        
        peer_pub = int.from_bytes(peer_public_key, 'big')
        
        # 验证对方公钥
        if peer_pub <= 1 or peer_pub >= self.PRIME - 1:
            raise ValueError("无效的对方公钥")
        
        # 计算共享密钥: B^a mod p
        shared = pow(peer_pub, self._private_key, self.PRIME)
        shared_bytes = shared.to_bytes(256, 'big')
        
        # 使用 SHA-256 派生密钥
        self._shared_secret = hashlib.sha256(shared_bytes).digest()
        return self._shared_secret
    
    @property
    def shared_secret(self) -> bytes:
        """获取共享密钥"""
        return self._shared_secret
    
    @property
    def public_key(self) -> bytes:
        """获取本方公钥"""
        if self._public_key:
            return self._public_key.to_bytes(256, 'big')
        return None


def derive_session_keys(shared_secret: bytes, client_random: bytes, server_random: bytes) -> dict:
    """
    从共享密钥派生会话密钥
    
    Args:
        shared_secret: DH 共享密钥
        client_random: 客户端随机数 (32 bytes)
        server_random: 服务端随机数 (32 bytes)
        
    Returns:
        包含多个派生密钥的字典
    """
    # 使用 HKDF 风格的密钥派生
    seed = shared_secret + client_random + server_random
    
    # 派生客户端加密密钥
    client_key = hashlib.sha256(b"client_key" + seed).digest()
    # 派生服务端加密密钥
    server_key = hashlib.sha256(b"server_key" + seed).digest()
    # 派生 HMAC 密钥
    hmac_key = hashlib.sha256(b"hmac_key" + seed).digest()
    
    return {
        'client_key': client_key,
        'server_key': server_key,
        'hmac_key': hmac_key
    }
