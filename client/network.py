"""
网络通信模块
处理与服务器的加密通信
"""

import json
import socket
from typing import Optional, Tuple, Callable
from dataclasses import dataclass

from protocol.packet import PacketType
from protocol.secure_channel import SecureChannel, SecureChannelBuilder


@dataclass
class ServerInfo:
    """服务器信息"""
    host: str = "localhost"
    port: int = 9000
    public_key: bytes = None


class NetworkClient:
    """网络客户端"""
    
    def __init__(self, server_info: ServerInfo):
        """
        初始化网络客户端
        
        Args:
            server_info: 服务器信息
        """
        self.server_info = server_info
        self.sock: Optional[socket.socket] = None
        self.channel: Optional[SecureChannel] = None
        self._connected = False
        self._auth_cache = {}  # 缓存登录凭据用于静默重连
    
    def connect(self) -> bool:
        """
        连接到服务器并建立安全通道
        
        Returns:
            是否连接成功
        """
        try:
            # 创建 socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(30)
            self.sock.connect((self.server_info.host, self.server_info.port))
            
            print(f"[Client] 已连接到 {self.server_info.host}:{self.server_info.port}")
            
            # 建立安全通道
            self.channel = SecureChannelBuilder.client_connect(
                self.sock,
                self.server_info.public_key
            )
            
            if not self.channel:
                print("[Client] 安全通道建立失败")
                self.sock.close()
                return False
            
            print("[Client] 安全通道已建立")
            self._connected = True
            return True
        except Exception as e:
            print(f"[Client] 连接失败: {e}")
            if self.sock:
                self.sock.close()
            return False
    
    def disconnect(self):
        """断开连接"""
        self._connected = False
        if self.channel:
            self.channel.close()
        elif self.sock:
            self.sock.close()
        self.channel = None
        self.sock = None
        print("[Client] 已断开连接")
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected and self.channel and not self.channel.is_closed
    
    def ping(self) -> bool:
        """测试连接实质连通性"""
        if not self.is_connected:
            return False
        try:
            result = self.send_request(PacketType.HEARTBEAT, {}, timeout=5)
            return result is not None and result.get('success', False)
        except:
            self._connected = False
            return False

    def send_request(self, packet_type: PacketType, 
                     data: dict, timeout: float = 30) -> Optional[dict]:
        """
        发送请求并等待响应
        
        Args:
            packet_type: 请求类型
            data: 请求数据
            timeout: 超时时间
            
        Returns:
            响应数据字典
        """
        if not self.is_connected:
            return {'success': False, 'error': '未连接到服务器'}
        
        try:
            # 发送请求
            payload = json.dumps(data).encode('utf-8')
            if not self.channel.send(packet_type, payload):
                return {'success': False, 'error': '发送请求失败'}
            
            # 等待响应
            result = self.channel.recv(timeout)
            if not result:
                return {'success': False, 'error': '接收响应超时'}
            
            response_type, response_data = result
            return json.loads(response_data.decode('utf-8'))
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'响应解析失败: {e}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_binary(self, packet_type: PacketType, 
                    data: bytes, timeout: float = 30) -> Optional[dict]:
        """
        发送二进制数据并等待响应
        
        Args:
            packet_type: 请求类型
            data: 二进制数据
            timeout: 超时时间
            
        Returns:
            响应数据字典
        """
        if not self.is_connected:
            return {'success': False, 'error': '未连接到服务器'}
        
        try:
            if not self.channel.send(packet_type, data):
                return {'success': False, 'error': '发送数据失败'}
            
            result = self.channel.recv(timeout)
            if not result:
                return {'success': False, 'error': '接收响应超时'}
            
            response_type, response_data = result
            return json.loads(response_data.decode('utf-8'))
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ============ API 方法 ============
    
    def register(self, username: str, email: str, password_hash: str,
                 public_key: str, encrypted_private_key: str,
                 encrypted_master_key: str, master_key_salt: str,
                 recovery_key_encrypted: str, recovery_key_salt: str,
                 recovery_key_hash: str) -> dict:
        """用户注册"""
        return self.send_request(PacketType.REGISTER_REQUEST, {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'public_key': public_key,
            'encrypted_private_key': encrypted_private_key,
            'private_key_salt': '',
            'encrypted_master_key': encrypted_master_key,
            'master_key_salt': master_key_salt,
            'recovery_key_encrypted': recovery_key_encrypted,
            'recovery_key_salt': recovery_key_salt,
            'recovery_key_hash': recovery_key_hash
        })
    
    def login_password(self, username: str, password: str) -> dict:
        """密码登录"""
        result = self.send_request(PacketType.AUTH_REQUEST, {
            'login_type': 'password',
            'username': username,
            'password': password  # 发送预哈希后的密码
        })
        if result.get('success'):
            self._auth_cache = {
                'login_type': 'password',
                'username': username,
                'password': password
            }
        return result
    
    def login_email(self, email: str, code: str) -> dict:
        """Email 验证码登录"""
        return self.send_request(PacketType.AUTH_REQUEST, {
            'login_type': 'email',
            'email': email,
            'code': code
        })
    
    def request_email_code(self, email: str, purpose: str = 'login') -> dict:
        """请求发送验证码"""
        return self.send_request(PacketType.EMAIL_CODE_REQUEST, {
            'email': email,
            'purpose': purpose
        })
    
    def get_user_for_recovery(self, username: str) -> dict:
        """获取用户恢复数据"""
        return self.send_request(PacketType.AUTH_REQUEST, {
            'login_type': 'recovery_data',
            'username': username
        })
    
    def reset_password(self, username: str = None, email: str = None, 
                       code: str = None, recovery_key: str = None,
                       new_password_hash: str = None,
                       new_encrypted_master_key: str = None,
                       new_master_key_salt: str = None) -> dict:
        """重置密码（支持邮箱验证码或恢复密钥）"""
        return self.send_request(PacketType.PASSWORD_RESET_REQUEST, {
            'username': username,
            'email': email,
            'code': code,
            'recovery_key': recovery_key,
            'new_password_hash': new_password_hash,
            'new_encrypted_master_key': new_encrypted_master_key,
            'new_master_key_salt': new_master_key_salt
        })
    
    def get_file_list(self, parent_id: int = None, group_id: int = None) -> dict:
        """获取文件列表"""
        return self.send_request(PacketType.FILE_LIST_REQUEST, {
            'parent_id': parent_id,
            'group_id': group_id
        })
    
    def upload_file_start(self, filename: str, size: int,
                          encrypted_file_key: str,
                          parent_id: int = None,
                          group_id: int = None) -> dict:
        """开始文件上传"""
        return self.send_request(PacketType.FILE_UPLOAD_START, {
            'filename': filename,
            'size': size,
            'encrypted_file_key': encrypted_file_key,
            'parent_id': parent_id,
            'group_id': group_id,
            'path': '/' + filename
        })
    
    def upload_file_data(self, upload_id: str, data: bytes) -> dict:
        """上传文件数据块"""
        payload = upload_id.encode('utf-8') + data
        return self.send_binary(PacketType.FILE_UPLOAD_DATA, payload)
    
    def upload_file_end(self, upload_id: str) -> dict:
        """结束文件上传"""
        return self.send_request(PacketType.FILE_UPLOAD_END, {
            'upload_id': upload_id
        })
    
    def upload_file_cancel(self, upload_id: str) -> dict:
        """取消文件上传"""
        return self.send_request(PacketType.FILE_UPLOAD_CANCEL, {
            'upload_id': upload_id
        })
    
    def download_file_start(self, file_id: int) -> dict:
        """开始文件下载 - 返回元数据"""
        return self.send_request(PacketType.FILE_DOWNLOAD_REQUEST, {
            'file_id': file_id
        }, timeout=60)
    
    def download_file_data(self, download_id: str, chunk_size: int = 256 * 1024) -> dict:
        """获取下载数据块"""
        return self.send_request(PacketType.FILE_DOWNLOAD_DATA, {
            'download_id': download_id,
            'chunk_size': chunk_size
        }, timeout=60)
    
    def delete_file(self, file_id: int) -> dict:
        """删除文件"""
        return self.send_request(PacketType.FILE_DELETE_REQUEST, {
            'file_id': file_id
        })
    
    def rename_file(self, file_id: int, new_name: str) -> dict:
        """重命名文件"""
        return self.send_request(PacketType.FILE_RENAME_REQUEST, {
            'file_id': file_id,
            'new_name': new_name
        })
    
    def create_folder(self, name: str, parent_id: int = None,
                      group_id: int = None) -> dict:
        """创建文件夹"""
        return self.send_request(PacketType.FOLDER_CREATE_REQUEST, {
            'name': name,
            'parent_id': parent_id,
            'group_id': group_id,
            'path': '/' + name
        })
    
    def create_group(self, name: str, encrypted_group_key: str = None) -> dict:
        """创建群组"""
        return self.send_request(PacketType.GROUP_CREATE_REQUEST, {
            'name': name,
            'encrypted_group_key': encrypted_group_key
        })
    
    def get_groups(self) -> dict:
        """获取群组列表"""
        return self.send_request(PacketType.GROUP_LIST_REQUEST, {})
    
    def invite_to_group(self, group_id: int, username: str,
                        encrypted_group_key: str) -> dict:
        """邀请用户加入群组"""
        return self.send_request(PacketType.GROUP_INVITE_REQUEST, {
            'group_id': group_id,
            'username': username,
            'encrypted_group_key': encrypted_group_key
        })
    
    def respond_invitation(self, invitation_id: int, accept: bool) -> dict:
        """响应群组邀请"""
        return self.send_request(PacketType.GROUP_JOIN_REQUEST, {
            'invitation_id': invitation_id,
            'accept': accept
        })
    
    def leave_group(self, group_id: int) -> dict:
        """退出群组"""
        return self.send_request(PacketType.GROUP_LEAVE_REQUEST, {
            'group_id': group_id
        })
    
    def get_group_members(self, group_id: int) -> dict:
        """获取群组成员"""
        return self.send_request(PacketType.GROUP_MEMBERS_REQUEST, {
            'group_id': group_id
        })
    
    def get_group_key(self, group_id: int) -> dict:
        """获取群组密钥"""
        return self.send_request(PacketType.GROUP_KEY_REQUEST, {
            'group_id': group_id
        })
    
    def get_user_public_key(self, username: str) -> dict:
        """获取用户公钥"""
        return self.send_request(PacketType.USER_PUBLIC_KEY_REQUEST, {
            'username': username
        })
    
    def get_notification_counts(self) -> dict:
        """获取未读通知计数"""
        return self.send_request(PacketType.NOTIFICATION_COUNT_REQUEST, {})
    
    def mark_notification_read(self, notification_type: str, group_id: int = None) -> dict:
        """标记通知已读"""
        return self.send_request(PacketType.NOTIFICATION_READ_REQUEST, {
            'type': notification_type,
            'group_id': group_id
        })
