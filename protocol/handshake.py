"""
握手协议实现
安全的密钥协商过程
"""

import os
import json
import struct
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import IntEnum

from crypto.dh import DHKeyExchange, derive_session_keys
from crypto.rsa import RSACipher
from crypto.hmac_auth import HMACAuth


class HandshakeState(IntEnum):
    """握手状态"""
    INITIAL = 0
    CLIENT_HELLO_SENT = 1
    SERVER_HELLO_SENT = 2
    KEY_EXCHANGED = 3
    FINISHED = 4
    FAILED = 5


@dataclass
class ClientHello:
    """客户端 Hello 消息"""
    client_random: bytes  # 32 字节随机数
    dh_public_key: bytes  # DH 公钥
    
    def to_bytes(self) -> bytes:
        return struct.pack('>I', len(self.client_random)) + self.client_random + \
               struct.pack('>I', len(self.dh_public_key)) + self.dh_public_key
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ClientHello':
        offset = 0
        random_len = struct.unpack('>I', data[offset:offset+4])[0]
        offset += 4
        client_random = data[offset:offset+random_len]
        offset += random_len
        
        dh_len = struct.unpack('>I', data[offset:offset+4])[0]
        offset += 4
        dh_public_key = data[offset:offset+dh_len]
        
        return cls(client_random=client_random, dh_public_key=dh_public_key)


@dataclass
class ServerHello:
    """服务端 Hello 消息"""
    server_random: bytes  # 32 字节随机数
    dh_public_key: bytes  # DH 公钥
    server_public_key: bytes  # 服务器 RSA 公钥（用于验证）
    signature: bytes  # 对 (client_random + server_random + dh_public_key) 的签名
    
    def to_bytes(self) -> bytes:
        result = b''
        result += struct.pack('>I', len(self.server_random)) + self.server_random
        result += struct.pack('>I', len(self.dh_public_key)) + self.dh_public_key
        result += struct.pack('>I', len(self.server_public_key)) + self.server_public_key
        result += struct.pack('>I', len(self.signature)) + self.signature
        return result
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'ServerHello':
        offset = 0
        
        random_len = struct.unpack('>I', data[offset:offset+4])[0]
        offset += 4
        server_random = data[offset:offset+random_len]
        offset += random_len
        
        dh_len = struct.unpack('>I', data[offset:offset+4])[0]
        offset += 4
        dh_public_key = data[offset:offset+dh_len]
        offset += dh_len
        
        pub_len = struct.unpack('>I', data[offset:offset+4])[0]
        offset += 4
        server_public_key = data[offset:offset+pub_len]
        offset += pub_len
        
        sig_len = struct.unpack('>I', data[offset:offset+4])[0]
        offset += 4
        signature = data[offset:offset+sig_len]
        
        return cls(
            server_random=server_random,
            dh_public_key=dh_public_key,
            server_public_key=server_public_key,
            signature=signature
        )


@dataclass  
class FinishedMessage:
    """握手完成消息"""
    verify_data: bytes  # 使用派生密钥加密的验证数据
    
    def to_bytes(self) -> bytes:
        return struct.pack('>I', len(self.verify_data)) + self.verify_data
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'FinishedMessage':
        length = struct.unpack('>I', data[:4])[0]
        verify_data = data[4:4+length]
        return cls(verify_data=verify_data)


class ClientHandshake:
    """客户端握手处理器"""
    
    def __init__(self, server_public_key: bytes = None):
        """
        初始化客户端握手
        
        Args:
            server_public_key: 预置的服务器公钥（用于验证防中间人攻击）
        """
        self.state = HandshakeState.INITIAL
        self.dh = DHKeyExchange()
        self.client_random = os.urandom(32)
        self.server_random = None
        self.session_keys = None
        self.known_server_key = server_public_key
    
    def create_client_hello(self) -> bytes:
        """
        创建 ClientHello 消息
        
        Returns:
            ClientHello 消息的字节表示
        """
        dh_public = self.dh.generate_keypair()
        hello = ClientHello(
            client_random=self.client_random,
            dh_public_key=dh_public
        )
        self.state = HandshakeState.CLIENT_HELLO_SENT
        return hello.to_bytes()
    
    def process_server_hello(self, data: bytes) -> bool:
        """
        处理 ServerHello 消息
        
        Args:
            data: ServerHello 消息的字节数据
            
        Returns:
            验证是否成功
        """
        if self.state != HandshakeState.CLIENT_HELLO_SENT:
            return False
        
        try:
            server_hello = ServerHello.from_bytes(data)
            self.server_random = server_hello.server_random
            
            # 如果有预置服务器公钥，验证是否匹配
            if self.known_server_key:
                if server_hello.server_public_key != self.known_server_key:
                    self.state = HandshakeState.FAILED
                    return False
            
            # 验证签名（防中间人攻击）
            sign_data = self.client_random + server_hello.server_random + server_hello.dh_public_key
            rsa = RSACipher(public_key=server_hello.server_public_key)
            if not rsa.verify(sign_data, server_hello.signature):
                self.state = HandshakeState.FAILED
                return False
            
            # 计算共享密钥
            shared_secret = self.dh.compute_shared_secret(server_hello.dh_public_key)
            
            # 派生会话密钥
            self.session_keys = derive_session_keys(
                shared_secret, 
                self.client_random, 
                self.server_random
            )
            
            self.state = HandshakeState.KEY_EXCHANGED
            return True
        except Exception as e:
            self.state = HandshakeState.FAILED
            return False
    
    def create_finished(self) -> bytes:
        """
        创建 Finished 消息
        
        Returns:
            Finished 消息的字节表示
        """
        if self.state != HandshakeState.KEY_EXCHANGED:
            return None
        
        # 验证数据：对所有握手消息的 HMAC
        verify_data = HMACAuth.quick_hmac(
            self.session_keys['hmac_key'],
            b"client_finished" + self.client_random + self.server_random
        )
        finished = FinishedMessage(verify_data=verify_data)
        return finished.to_bytes()
    
    def process_server_finished(self, data: bytes) -> bool:
        """
        处理服务端 Finished 消息
        
        Args:
            data: Finished 消息的字节数据
            
        Returns:
            验证是否成功
        """
        if self.state != HandshakeState.KEY_EXCHANGED:
            return False
        
        try:
            finished = FinishedMessage.from_bytes(data)
            
            # 验证服务端的 verify_data
            expected = HMACAuth.quick_hmac(
                self.session_keys['hmac_key'],
                b"server_finished" + self.client_random + self.server_random
            )
            
            if finished.verify_data == expected:
                self.state = HandshakeState.FINISHED
                return True
            else:
                self.state = HandshakeState.FAILED
                return False
        except Exception:
            self.state = HandshakeState.FAILED
            return False


class ServerHandshake:
    """服务端握手处理器"""
    
    def __init__(self, server_private_key: bytes, server_public_key: bytes):
        """
        初始化服务端握手
        
        Args:
            server_private_key: 服务器 RSA 私钥
            server_public_key: 服务器 RSA 公钥
        """
        self.state = HandshakeState.INITIAL
        self.dh = DHKeyExchange()
        self.server_random = os.urandom(32)
        self.client_random = None
        self.session_keys = None
        self.rsa = RSACipher(private_key=server_private_key)
        self.server_public_key = server_public_key
    
    def process_client_hello(self, data: bytes) -> bytes:
        """
        处理 ClientHello 并返回 ServerHello
        
        Args:
            data: ClientHello 消息的字节数据
            
        Returns:
            ServerHello 消息的字节表示
        """
        try:
            client_hello = ClientHello.from_bytes(data)
            self.client_random = client_hello.client_random
            
            # 生成 DH 密钥对
            dh_public = self.dh.generate_keypair()
            
            # 计算共享密钥
            shared_secret = self.dh.compute_shared_secret(client_hello.dh_public_key)
            
            # 派生会话密钥
            self.session_keys = derive_session_keys(
                shared_secret,
                self.client_random,
                self.server_random
            )
            
            # 签名验证数据（防中间人攻击）
            sign_data = self.client_random + self.server_random + dh_public
            signature = self.rsa.sign(sign_data)
            
            server_hello = ServerHello(
                server_random=self.server_random,
                dh_public_key=dh_public,
                server_public_key=self.server_public_key,
                signature=signature
            )
            
            self.state = HandshakeState.SERVER_HELLO_SENT
            return server_hello.to_bytes()
        except Exception as e:
            self.state = HandshakeState.FAILED
            return None
    
    def process_client_finished(self, data: bytes) -> bytes:
        """
        处理客户端 Finished 并返回服务端 Finished
        
        Args:
            data: 客户端 Finished 消息的字节数据
            
        Returns:
            服务端 Finished 消息的字节表示，验证失败返回 None
        """
        if self.state != HandshakeState.SERVER_HELLO_SENT:
            return None
        
        try:
            finished = FinishedMessage.from_bytes(data)
            
            # 验证客户端的 verify_data
            expected = HMACAuth.quick_hmac(
                self.session_keys['hmac_key'],
                b"client_finished" + self.client_random + self.server_random
            )
            
            if finished.verify_data != expected:
                self.state = HandshakeState.FAILED
                return None
            
            self.state = HandshakeState.KEY_EXCHANGED
            
            # 生成服务端 Finished
            verify_data = HMACAuth.quick_hmac(
                self.session_keys['hmac_key'],
                b"server_finished" + self.client_random + self.server_random
            )
            
            self.state = HandshakeState.FINISHED
            return FinishedMessage(verify_data=verify_data).to_bytes()
        except Exception:
            self.state = HandshakeState.FAILED
            return None
