"""
安全通道模块
封装加密传输的完整逻辑
"""

import os
import socket
import struct
import threading
from typing import Optional, Tuple, Callable
from queue import Queue

from crypto.aes import AESCipher
from crypto.hmac_auth import HMACAuth
from .packet import Packet, PacketType, PacketBuilder, PacketFlags, HEADER_SIZE
from .session import Session


class SecureChannel:
    """安全通道 - 封装加密通信"""
    
    MAX_PAYLOAD_SIZE = 65536  # 最大载荷大小
    RECV_BUFFER_SIZE = 4096   # 接收缓冲区大小
    
    def __init__(self, sock: socket.socket, session: Session, is_server: bool = False):
        """
        初始化安全通道
        
        Args:
            sock: 底层 socket
            session: 已建立的会话
            is_server: 是否为服务端
        """
        self.sock = sock
        self.session = session
        self.is_server = is_server
        self.packet_builder = PacketBuilder()
        self._recv_buffer = b''
        self._lock = threading.Lock()
        self._closed = False
    
    @property
    def encrypt_key(self) -> bytes:
        """获取加密密钥"""
        return self.session.server_key if self.is_server else self.session.client_key
    
    @property
    def decrypt_key(self) -> bytes:
        """获取解密密钥"""
        return self.session.client_key if self.is_server else self.session.server_key
    
    def send(self, packet_type: PacketType, payload: bytes) -> bool:
        """
        发送加密数据
        
        Args:
            packet_type: 数据包类型
            payload: 原始载荷数据
            
        Returns:
            发送是否成功
        """
        if self._closed:
            return False
        
        try:
            with self._lock:
                # 加密载荷
                cipher = AESCipher(self.encrypt_key)
                encrypted_payload, nonce = cipher.encrypt_ctr(payload)
                
                # nonce 放在密文前面
                full_payload = nonce + encrypted_payload
                
                # 获取序列号
                if self.is_server:
                    sequence = self.session.next_server_sequence()
                else:
                    self.session.client_sequence += 1
                    sequence = self.session.client_sequence
                
                # 构建数据包
                packet = Packet(
                    packet_type=packet_type,
                    payload=full_payload,
                    flags=PacketFlags.ENCRYPTED,
                    sequence=sequence
                )
                
                # 计算 HMAC
                hmac_data = packet.get_hmac_data()
                packet.hmac = HMACAuth.quick_hmac(self.session.hmac_key, hmac_data)
                
                # 发送
                data = packet.to_bytes()
                self._send_all(data)
                return True
        except Exception as e:
            return False
    
    def recv(self, timeout: float = None) -> Optional[Tuple[PacketType, bytes]]:
        """
        接收并解密数据
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            (数据包类型, 解密后的载荷) 元组，失败返回 None
        """
        if self._closed:
            return None
        
        try:
            if timeout:
                self.sock.settimeout(timeout)
            
            # 读取完整数据包
            packet = self._recv_packet()
            if not packet:
                return None
            
            # 验证 HMAC
            hmac_data = packet.get_hmac_data()
            if not HMACAuth.quick_verify(self.session.hmac_key, hmac_data, packet.hmac):
                return None  # HMAC 验证失败
            
            # 验证序列号（防重放）
            is_from_client = not self.is_server
            if not self.session.validate_sequence(packet.sequence, is_from_client):
                return None  # 序列号无效
            
            # 验证时间戳
            if not self.session.validate_timestamp(packet.timestamp):
                return None  # 时间戳无效
            
            # 解密载荷
            if packet.is_encrypted and len(packet.payload) > 8:
                nonce = packet.payload[:8]
                encrypted = packet.payload[8:]
                cipher = AESCipher(self.decrypt_key)
                payload = cipher.decrypt_ctr(encrypted, nonce)
            else:
                payload = packet.payload
            
            self.session.update_activity()
            return (packet.packet_type, payload)
        except socket.timeout:
            return None
        except Exception as e:
            return None
        finally:
            if timeout:
                self.sock.settimeout(None)
    
    def _send_all(self, data: bytes):
        """确保完整发送数据"""
        total_sent = 0
        while total_sent < len(data):
            sent = self.sock.send(data[total_sent:])
            if sent == 0:
                raise ConnectionError("连接已断开")
            total_sent += sent
    
    def _recv_packet(self) -> Optional[Packet]:
        """接收完整的数据包"""
        # 先接收头部
        while len(self._recv_buffer) < HEADER_SIZE:
            try:
                chunk = self.sock.recv(self.RECV_BUFFER_SIZE)
                if not chunk:
                    return None
                self._recv_buffer += chunk
            except Exception:
                return None
        
        # 解析载荷长度
        payload_len = struct.unpack('>I', self._recv_buffer[20:24])[0]
        total_size = HEADER_SIZE + payload_len
        
        # 接收完整数据包
        while len(self._recv_buffer) < total_size:
            try:
                chunk = self.sock.recv(self.RECV_BUFFER_SIZE)
                if not chunk:
                    return None
                self._recv_buffer += chunk
            except Exception:
                return None
        
        # 提取数据包
        packet_data = self._recv_buffer[:total_size]
        self._recv_buffer = self._recv_buffer[total_size:]
        
        return Packet.from_bytes(packet_data)
    
    def send_raw(self, packet: Packet) -> bool:
        """
        发送原始数据包（用于握手阶段）
        
        Args:
            packet: 要发送的数据包
            
        Returns:
            发送是否成功
        """
        try:
            with self._lock:
                # 计算 HMAC（如果有密钥）
                if self.session and self.session.hmac_key:
                    hmac_data = packet.get_hmac_data()
                    packet.hmac = HMACAuth.quick_hmac(self.session.hmac_key, hmac_data)
                
                data = packet.to_bytes()
                self._send_all(data)
                return True
        except Exception:
            return False
    
    def recv_raw(self, timeout: float = None) -> Optional[Packet]:
        """
        接收原始数据包（用于握手阶段）
        
        Args:
            timeout: 超时时间
            
        Returns:
            接收到的数据包
        """
        try:
            if timeout:
                self.sock.settimeout(timeout)
            return self._recv_packet()
        except socket.timeout:
            return None
        except Exception:
            return None
        finally:
            if timeout:
                self.sock.settimeout(None)
    
    def close(self):
        """关闭通道"""
        self._closed = True
        try:
            self.sock.close()
        except Exception:
            pass
    
    @property
    def is_closed(self) -> bool:
        """通道是否已关闭"""
        return self._closed


class SecureChannelBuilder:
    """安全通道构建器 - 处理握手过程"""
    
    @staticmethod
    def client_connect(sock: socket.socket, 
                       server_public_key: bytes = None) -> Optional[SecureChannel]:
        """
        客户端建立安全连接
        
        Args:
            sock: 已连接的 socket
            server_public_key: 服务器公钥（可选，用于验证）
            
        Returns:
            建立的安全通道，失败返回 None
        """
        from .handshake import ClientHandshake
        
        try:
            handshake = ClientHandshake(server_public_key)
            
            # 发送 ClientHello
            client_hello = handshake.create_client_hello()
            hello_packet = Packet(
                packet_type=PacketType.CLIENT_HELLO,
                payload=client_hello,
                flags=0
            )
            sock.sendall(hello_packet.to_bytes())
            
            # 接收 ServerHello
            server_hello_data = SecureChannelBuilder._recv_packet_data(sock)
            if not server_hello_data:
                return None
            
            server_hello_packet = Packet.from_bytes(server_hello_data)
            if not server_hello_packet or server_hello_packet.packet_type != PacketType.SERVER_HELLO:
                return None
            
            if not handshake.process_server_hello(server_hello_packet.payload):
                return None
            
            # 创建临时会话用于加密
            session = Session(
                session_id=os.urandom(16).hex(),
                client_key=handshake.session_keys['client_key'],
                server_key=handshake.session_keys['server_key'],
                hmac_key=handshake.session_keys['hmac_key']
            )
            
            # 发送 ClientFinished
            finished = handshake.create_finished()
            finished_packet = Packet(
                packet_type=PacketType.FINISHED,
                payload=finished,
                flags=0
            )
            # 为 Finished 消息计算 HMAC
            hmac_data = finished_packet.get_hmac_data()
            finished_packet.hmac = HMACAuth.quick_hmac(session.hmac_key, hmac_data)
            sock.sendall(finished_packet.to_bytes())
            
            # 接收 ServerFinished
            server_finished_data = SecureChannelBuilder._recv_packet_data(sock)
            if not server_finished_data:
                return None
            
            server_finished_packet = Packet.from_bytes(server_finished_data)
            if not server_finished_packet or server_finished_packet.packet_type != PacketType.FINISHED:
                return None
            
            if not handshake.process_server_finished(server_finished_packet.payload):
                return None
            
            return SecureChannel(sock, session, is_server=False)
        except Exception as e:
            return None
    
    @staticmethod
    def _recv_packet_data(sock: socket.socket) -> Optional[bytes]:
        """接收原始数据包数据"""
        try:
            # 读取头部
            header = b''
            while len(header) < HEADER_SIZE:
                chunk = sock.recv(HEADER_SIZE - len(header))
                if not chunk:
                    return None
                header += chunk
            
            # 解析载荷长度
            payload_len = struct.unpack('>I', header[20:24])[0]
            
            # 读取载荷
            payload = b''
            while len(payload) < payload_len:
                chunk = sock.recv(payload_len - len(payload))
                if not chunk:
                    return None
                payload += chunk
            
            return header + payload
        except Exception:
            return None
