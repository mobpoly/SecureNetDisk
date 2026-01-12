"""
TCP 服务器模块
处理客户端连接和消息路由
"""

import os
import socket
import selectors
import threading
import traceback
from typing import Dict, Callable, Optional
from dataclasses import dataclass

from crypto.rsa import RSACipher
from protocol.packet import Packet, PacketType, HEADER_SIZE
from protocol.handshake import ServerHandshake, HandshakeState
from protocol.session import Session, SessionManager
from protocol.secure_channel import SecureChannel
from .config import ServerConfig


@dataclass
class ClientConnection:
    """客户端连接"""
    sock: socket.socket
    addr: tuple
    handshake: Optional[ServerHandshake] = None
    channel: Optional[SecureChannel] = None
    session: Optional[Session] = None
    recv_buffer: bytes = b''


class TCPServer:
    """TCP 服务器"""
    
    def __init__(self, config: ServerConfig, handler: Callable = None):
        """
        初始化 TCP 服务器
        
        Args:
            config: 服务器配置
            handler: 消息处理器函数
        """
        self.config = config
        self.handler = handler
        self.selector = selectors.DefaultSelector()
        self.session_manager = SessionManager()
        self.connections: Dict[socket.socket, ClientConnection] = {}
        self._running = False
        self._server_socket = None
        
        # 加载或生成服务器密钥
        self._load_server_keys()
    
    def _load_server_keys(self):
        """加载或生成服务器 RSA 密钥对"""
        priv_path = self.config.server_private_key_path
        pub_path = self.config.server_public_key_path
        
        if priv_path.exists() and pub_path.exists():
            with open(priv_path, 'rb') as f:
                self.server_private_key = f.read()
            with open(pub_path, 'rb') as f:
                self.server_public_key = f.read()
            print(f"[Server] 已加载服务器密钥")
        else:
            # 生成新密钥对
            self.server_private_key, self.server_public_key = RSACipher.generate_keypair()
            
            # 保存密钥
            priv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(priv_path, 'wb') as f:
                f.write(self.server_private_key)
            with open(pub_path, 'wb') as f:
                f.write(self.server_public_key)
            print(f"[Server] 已生成新服务器密钥对")
    
    def start(self):
        """启动服务器"""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.config.host, self.config.port))
        self._server_socket.listen(self.config.max_connections)
        self._server_socket.setblocking(False)
        
        self.selector.register(self._server_socket, selectors.EVENT_READ, self._accept)
        
        self._running = True
        print(f"[Server] 服务器启动于 {self.config.host}:{self.config.port}")
        print(f"[Server] 服务器公钥指纹: {self._get_key_fingerprint()}")
        
        self._run_loop()
    
    def _get_key_fingerprint(self) -> str:
        """获取服务器公钥指纹"""
        import hashlib
        return hashlib.sha256(self.server_public_key).hexdigest()[:16].upper()
    
    def _run_loop(self):
        """主事件循环"""
        while self._running:
            try:
                events = self.selector.select(timeout=1)
                for key, mask in events:
                    callback = key.data
                    callback(key.fileobj)
            except Exception as e:
                if self._running:
                    print(f"[Server] 事件循环错误: {e}")
    
    def _accept(self, sock: socket.socket):
        """接受新连接"""
        try:
            conn, addr = sock.accept()
            conn.setblocking(False)
            
            client = ClientConnection(sock=conn, addr=addr)
            self.connections[conn] = client
            
            self.selector.register(conn, selectors.EVENT_READ, self._handle_client)
            print(f"[Server] 新连接: {addr}")
        except Exception as e:
            print(f"[Server] 接受连接错误: {e}")
    
    def _handle_client(self, sock: socket.socket):
        """处理客户端消息"""
        client = self.connections.get(sock)
        if not client:
            return
        
        try:
            data = sock.recv(4096)
            if not data:
                self._disconnect(sock)
                return
            
            client.recv_buffer += data
            self._process_buffer(client)
        except ConnectionResetError:
            self._disconnect(sock)
        except Exception as e:
            print(f"[Server] 处理客户端错误: {e}")
            traceback.print_exc()
            self._disconnect(sock)
    
    def _process_buffer(self, client: ClientConnection):
        """处理接收缓冲区"""
        while len(client.recv_buffer) >= HEADER_SIZE:
            # 检查是否有完整数据包
            import struct
            payload_len = struct.unpack('>I', client.recv_buffer[20:24])[0]
            total_size = HEADER_SIZE + payload_len
            
            if len(client.recv_buffer) < total_size:
                break
            
            # 提取数据包
            packet_data = client.recv_buffer[:total_size]
            client.recv_buffer = client.recv_buffer[total_size:]
            
            packet = Packet.from_bytes(packet_data)
            if packet:
                self._handle_packet(client, packet)
    
    def _handle_packet(self, client: ClientConnection, packet: Packet):
        """处理单个数据包"""
        # 握手阶段
        if packet.packet_type == PacketType.CLIENT_HELLO:
            self._handle_client_hello(client, packet)
        elif packet.packet_type == PacketType.FINISHED and client.handshake:
            self._handle_client_finished(client, packet)
        elif client.channel:
            # 已建立安全通道，解密处理
            self._handle_secure_packet(client, packet)
        else:
            print(f"[Server] 收到意外数据包: {packet.packet_type}")
    
    def _handle_client_hello(self, client: ClientConnection, packet: Packet):
        """处理 ClientHello"""
        try:
            handshake = ServerHandshake(
                self.server_private_key,
                self.server_public_key
            )
            
            server_hello = handshake.process_client_hello(packet.payload)
            if not server_hello:
                self._disconnect(client.sock)
                return
            
            client.handshake = handshake
            
            # 发送 ServerHello
            response = Packet(
                packet_type=PacketType.SERVER_HELLO,
                payload=server_hello,
                flags=0
            )
            client.sock.sendall(response.to_bytes())
        except Exception as e:
            print(f"[Server] ClientHello 处理错误: {e}")
            self._disconnect(client.sock)
    
    def _handle_client_finished(self, client: ClientConnection, packet: Packet):
        """处理 ClientFinished"""
        try:
            server_finished = client.handshake.process_client_finished(packet.payload)
            if not server_finished:
                self._disconnect(client.sock)
                return
            
            # 创建会话
            session = self.session_manager.create_session(
                os.urandom(16).hex(),
                client.handshake.session_keys
            )
            client.session = session
            
            # 创建安全通道
            client.channel = SecureChannel(client.sock, session, is_server=True)
            
            # 发送 ServerFinished
            from crypto.hmac_auth import HMACAuth
            response = Packet(
                packet_type=PacketType.FINISHED,
                payload=server_finished,
                flags=0
            )
            hmac_data = response.get_hmac_data()
            response.hmac = HMACAuth.quick_hmac(session.hmac_key, hmac_data)
            client.sock.sendall(response.to_bytes())
            
            print(f"[Server] 握手完成: {client.addr}")
        except Exception as e:
            print(f"[Server] ClientFinished 处理错误: {e}")
            self._disconnect(client.sock)
    
    def _handle_secure_packet(self, client: ClientConnection, packet: Packet):
        """处理安全数据包"""
        try:
            from crypto.hmac_auth import HMACAuth
            from crypto.aes import AESCipher
            
            # 验证 HMAC
            hmac_data = packet.get_hmac_data()
            if not HMACAuth.quick_verify(client.session.hmac_key, hmac_data, packet.hmac):
                print(f"[Server] HMAC 验证失败")
                return
            
            # 验证序列号
            if not client.session.validate_sequence(packet.sequence, is_client=True):
                print(f"[Server] 序列号验证失败")
                return
            
            # 验证时间戳
            if not client.session.validate_timestamp(packet.timestamp):
                print(f"[Server] 时间戳验证失败")
                return
            
            # 解密载荷
            if packet.is_encrypted and len(packet.payload) > 8:
                nonce = packet.payload[:8]
                encrypted = packet.payload[8:]
                cipher = AESCipher(client.session.client_key)
                payload = cipher.decrypt_ctr(encrypted, nonce)
            else:
                payload = packet.payload
            
            # 调用处理器
            if self.handler:
                response_type, response_data = self.handler(
                    client.session, packet.packet_type, payload
                )
                if response_type and response_data is not None:
                    self._send_response(client, response_type, response_data)
            
            client.session.update_activity()
        except Exception as e:
            print(f"[Server] 安全数据包处理错误: {e}")
            traceback.print_exc()
    
    def _send_response(self, client: ClientConnection, 
                       packet_type: PacketType, payload: bytes):
        """发送加密响应"""
        if client.channel:
            client.channel.send(packet_type, payload)
    
    def _disconnect(self, sock: socket.socket):
        """断开连接"""
        client = self.connections.pop(sock, None)
        if client:
            print(f"[Server] 断开连接: {client.addr}")
            if client.session:
                self.session_manager.remove_session(client.session.session_id)
        
        try:
            self.selector.unregister(sock)
        except Exception:
            pass
        
        try:
            sock.close()
        except Exception:
            pass
    
    def stop(self):
        """停止服务器"""
        self._running = False
        
        # 断开所有连接
        for sock in list(self.connections.keys()):
            self._disconnect(sock)
        
        if self._server_socket:
            try:
                self.selector.unregister(self._server_socket)
                self._server_socket.close()
            except Exception:
                pass
        
        self.selector.close()
        self.session_manager.shutdown()
        print("[Server] 服务器已停止")
