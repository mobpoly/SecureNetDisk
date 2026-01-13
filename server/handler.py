"""
请求处理器模块
处理各种客户端请求
"""

import json
import os
from typing import Tuple, Optional
from datetime import datetime

from protocol.packet import PacketType
from protocol.session import Session
from auth.user import User
from auth.password import PasswordManager
from auth.email_service import EmailService
from crypto.rsa import RSACipher
from .database import Database
from .file_storage import FileStorage
from .config import ServerConfig


class RequestHandler:
    """请求处理器"""
    
    def __init__(self, config: ServerConfig):
        """
        初始化请求处理器
        
        Args:
            config: 服务器配置
        """
        self.config = config
        self.db = Database(config.database_path)
        self.storage = FileStorage(config.base_path)
        self.email_service = EmailService(
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_user=config.smtp_user,
            smtp_password=config.smtp_password
        )
        
        # 文件上传/下载会话
        self._upload_sessions = {}
        self._download_sessions = {}
    
    def handle(self, session: Session, packet_type: PacketType, 
               payload: bytes) -> Tuple[Optional[PacketType], Optional[bytes]]:
        """
        处理请求
        
        Args:
            session: 会话对象
            packet_type: 请求类型
            payload: 请求载荷
            
        Returns:
            (响应类型, 响应载荷) 元组
        """
        handlers = {
            # 认证
            PacketType.REGISTER_REQUEST: self._handle_register,
            PacketType.AUTH_REQUEST: self._handle_login,
            PacketType.EMAIL_CODE_REQUEST: self._handle_email_code,
            PacketType.PASSWORD_RESET_REQUEST: self._handle_password_reset,
            
            # 文件操作
            PacketType.FILE_LIST_REQUEST: self._handle_file_list,
            PacketType.FILE_UPLOAD_START: self._handle_upload_start,
            PacketType.FILE_UPLOAD_DATA: self._handle_upload_data,
            PacketType.FILE_UPLOAD_END: self._handle_upload_end,
            PacketType.FILE_UPLOAD_CANCEL: self._handle_upload_cancel,
            PacketType.FILE_DOWNLOAD_REQUEST: self._handle_download_request,
            PacketType.FILE_DOWNLOAD_DATA: self._handle_download_data,
            PacketType.FILE_DELETE_REQUEST: self._handle_delete,
            PacketType.FILE_RENAME_REQUEST: self._handle_rename,
            PacketType.FOLDER_CREATE_REQUEST: self._handle_create_folder,
            
            # 群组操作
            PacketType.GROUP_CREATE_REQUEST: self._handle_group_create,
            PacketType.GROUP_LIST_REQUEST: self._handle_group_list,
            PacketType.GROUP_INVITE_REQUEST: self._handle_group_invite,
            PacketType.GROUP_JOIN_REQUEST: self._handle_group_join,
            PacketType.GROUP_LEAVE_REQUEST: self._handle_group_leave,
            PacketType.GROUP_KEY_REQUEST: self._handle_group_key,
            PacketType.GROUP_MEMBERS_REQUEST: self._handle_group_members,
            
            # 用户信息
            PacketType.USER_PUBLIC_KEY_REQUEST: self._handle_user_public_key,
            
            # 通知
            PacketType.NOTIFICATION_COUNT_REQUEST: self._handle_notification_count,
            PacketType.NOTIFICATION_READ_REQUEST: self._handle_notification_read,
        }
        
        handler = handlers.get(packet_type)
        if handler:
            try:
                return handler(session, payload)
            except Exception as e:
                print(f"[Handler] 处理请求错误: {e}")
                import traceback
                traceback.print_exc()
                return self._error_response(str(e))
        
        return None, None
    
    def _error_response(self, message: str) -> Tuple[PacketType, bytes]:
        """生成错误响应"""
        return PacketType.ERROR, json.dumps({
            'success': False,
            'error': message
        }).encode('utf-8')
    
    def _success_response(self, data: dict = None) -> bytes:
        """生成成功响应"""
        response = {'success': True}
        if data:
            response.update(data)
        return json.dumps(response).encode('utf-8')
    
    # ============ 认证处理 ============
    
    def _handle_register(self, session: Session, 
                         payload: bytes) -> Tuple[PacketType, bytes]:
        """处理注册请求"""
        try:
            data = json.loads(payload.decode('utf-8'))
            
            username = data['username']
            email = data['email']
            password_hash = bytes.fromhex(data['password_hash'])
            
            # 检查用户名和邮箱是否已存在
            if self.db.get_user_by_username(username):
                return PacketType.REGISTER_RESPONSE, json.dumps({
                    'success': False,
                    'error': '用户名已存在'
                }).encode()
            
            if self.db.get_user_by_email(email):
                return PacketType.REGISTER_RESPONSE, json.dumps({
                    'success': False,
                    'error': '邮箱已被注册'
                }).encode()
            
            # 创建用户
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                public_key=bytes.fromhex(data['public_key']),
                encrypted_private_key=bytes.fromhex(data['encrypted_private_key']),
                private_key_salt=bytes.fromhex(data.get('private_key_salt', '')),
                encrypted_master_key=bytes.fromhex(data['encrypted_master_key']),
                master_key_salt=bytes.fromhex(data['master_key_salt']),
                recovery_key_encrypted=bytes.fromhex(data['recovery_key_encrypted']),
                recovery_key_salt=bytes.fromhex(data['recovery_key_salt']),
                recovery_key_hash=bytes.fromhex(data['recovery_key_hash'])
            )
            
            user_id = self.db.create_user(user)
            
            return PacketType.REGISTER_RESPONSE, json.dumps({
                'success': True,
                'user_id': user_id
            }).encode()
        except Exception as e:
            return PacketType.REGISTER_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_login(self, session: Session, 
                      payload: bytes) -> Tuple[PacketType, bytes]:
        """处理登录请求"""
        try:
            data = json.loads(payload.decode('utf-8'))
            login_type = data.get('login_type', 'password')
            
            if login_type == 'password':
                return self._handle_password_login(session, data)
            elif login_type == 'email':
                return self._handle_email_login(session, data)
            elif login_type == 'recovery_data':
                return self._handle_recovery_data(session, data)
            else:
                return PacketType.AUTH_RESPONSE, json.dumps({
                    'success': False,
                    'error': '不支持的登录方式'
                }).encode()
        except Exception as e:
            return PacketType.AUTH_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_password_login(self, session: Session, 
                               data: dict) -> Tuple[PacketType, bytes]:
        """处理密码登录"""
        username = data.get('username', '')
        password_prehash = data.get('password', '')  # 接收 SHA-256 预哈希后的密码
        
        user = self.db.get_user_by_username(username)
        if not user:
            return PacketType.AUTH_RESPONSE, json.dumps({
                'success': False,
                'error': '用户名或密码错误'
            }).encode()
        
        # 使用 bcrypt 验证预哈希后的密码
        if not PasswordManager.verify_password(password_prehash, user.password_hash):
            return PacketType.AUTH_RESPONSE, json.dumps({
                'success': False,
                'error': '用户名或密码错误'
            }).encode()
        
        # 绑定会话
        session.user_id = user.id
        session.username = user.username
        
        # 更新最后登录时间
        self.db.update_last_login(user.id)
        
        return PacketType.AUTH_RESPONSE, json.dumps({
            'success': True,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'public_key': user.public_key.hex(),
            'encrypted_private_key': user.encrypted_private_key.hex(),
            'encrypted_master_key': user.encrypted_master_key.hex(),
            'master_key_salt': user.master_key_salt.hex()
        }).encode()
    
    def _handle_email_login(self, session: Session, 
                            data: dict) -> Tuple[PacketType, bytes]:
        """处理邮箱验证码登录"""
        email = data.get('email', '')
        code = data.get('code', '')
        
        # 验证验证码
        valid, error = self.email_service.verify_code(email, code, 'login')
        if not valid:
            return PacketType.AUTH_RESPONSE, json.dumps({
                'success': False,
                'error': error
            }).encode()
        
        user = self.db.get_user_by_email(email)
        if not user:
            return PacketType.AUTH_RESPONSE, json.dumps({
                'success': False,
                'error': '用户不存在'
            }).encode()
        
        # 绑定会话
        session.user_id = user.id
        session.username = user.username
        
        self.db.update_last_login(user.id)
        
        return PacketType.AUTH_RESPONSE, json.dumps({
            'success': True,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'public_key': user.public_key.hex(),
            'encrypted_private_key': user.encrypted_private_key.hex(),
            'encrypted_master_key': user.encrypted_master_key.hex(),
            'master_key_salt': user.master_key_salt.hex()
        }).encode()
    
    def _handle_email_code(self, session: Session, 
                           payload: bytes) -> Tuple[PacketType, bytes]:
        """处理发送验证码请求"""
        try:
            data = json.loads(payload.decode('utf-8'))
            email = data['email']
            purpose = data.get('purpose', 'login')
            
            # 验证邮箱存在（登录时）
            if purpose == 'login':
                user = self.db.get_user_by_email(email)
                if not user:
                    return PacketType.EMAIL_CODE_RESPONSE, json.dumps({
                        'success': False,
                        'error': '该邮箱未注册'
                    }).encode()
            
            success, result = self.email_service.send_verification_code(email, purpose)
            
            return PacketType.EMAIL_CODE_RESPONSE, json.dumps({
                'success': success,
                'message': '验证码已发送' if success else result
            }).encode()
        except Exception as e:
            return PacketType.EMAIL_CODE_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_recovery_data(self, session: Session, 
                               data: dict) -> Tuple[PacketType, bytes]:
        """处理获取恢复数据请求"""
        username = data.get('username', '')
        
        user = self.db.get_user_by_username(username)
        if not user:
            return PacketType.AUTH_RESPONSE, json.dumps({
                'success': False,
                'error': '用户不存在'
            }).encode()
        
        # 返回恢复所需的数据（包括解锁密钥管理器需要的所有字段）
        return PacketType.AUTH_RESPONSE, json.dumps({
            'success': True,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'public_key': user.public_key.hex() if user.public_key else '',
            'encrypted_private_key': user.encrypted_private_key.hex() if user.encrypted_private_key else '',
            'encrypted_master_key': user.encrypted_master_key.hex() if user.encrypted_master_key else '',
            'master_key_salt': user.master_key_salt.hex() if user.master_key_salt else '',
            'recovery_key_encrypted': user.recovery_key_encrypted.hex() if user.recovery_key_encrypted else '',
            'recovery_key_salt': user.recovery_key_salt.hex() if user.recovery_key_salt else '',
            'recovery_key_hash': user.recovery_key_hash.hex() if user.recovery_key_hash else ''
        }).encode()
    
    def _handle_password_reset(self, session: Session, 
                               payload: bytes) -> Tuple[PacketType, bytes]:
        """处理密码重置请求（支持邮箱验证码或恢复密钥）"""
        try:
            data = json.loads(payload.decode('utf-8'))
            username = data.get('username')
            email = data.get('email')
            code = data.get('code')
            recovery_key = data.get('recovery_key')
            new_password_hash = bytes.fromhex(data['new_password_hash'])
            new_encrypted_master_key = bytes.fromhex(data['new_encrypted_master_key'])
            new_master_key_salt = bytes.fromhex(data['new_master_key_salt'])
            
            user = None
            
            # 使用恢复密钥重置
            if recovery_key and username:
                user = self.db.get_user_by_username(username)
                if not user:
                    return PacketType.PASSWORD_RESET_RESPONSE, json.dumps({
                        'success': False,
                        'error': '用户不存在'
                    }).encode()
                
                # 验证恢复密钥
                # 注意：存储的是 SHA256(normalized_recovery_key)，不是 PBKDF2 派生后的哈希
                import hashlib
                import secrets
                
                if user.recovery_key_hash:
                    # 标准化恢复密钥（移除分隔符，转大写）
                    recovery_normalized = recovery_key.replace('-', '').replace(' ', '').upper()
                    # 直接哈希标准化后的恢复密钥
                    computed_hash = hashlib.sha256(recovery_normalized.encode()).digest()
                    
                    if not secrets.compare_digest(computed_hash, user.recovery_key_hash):
                        return PacketType.PASSWORD_RESET_RESPONSE, json.dumps({
                            'success': False,
                            'error': '恢复密钥无效'
                        }).encode()
            
            # 使用邮箱验证码重置
            elif email and code:
                valid, error = self.email_service.verify_code(email, code, 'reset')
                if not valid:
                    return PacketType.PASSWORD_RESET_RESPONSE, json.dumps({
                        'success': False,
                        'error': error
                    }).encode()
                
                user = self.db.get_user_by_email(email)
                if not user:
                    return PacketType.PASSWORD_RESET_RESPONSE, json.dumps({
                        'success': False,
                        'error': '用户不存在'
                    }).encode()
            
            # 已登录用户修改密码（通过验证旧密码）
            elif session.user_id and username:
                user = self.db.get_user_by_username(username)
                if not user or user.id != session.user_id:
                    return PacketType.PASSWORD_RESET_RESPONSE, json.dumps({
                        'success': False,
                        'error': '用户验证失败'
                    }).encode()
            
            else:
                return PacketType.PASSWORD_RESET_RESPONSE, json.dumps({
                    'success': False,
                    'error': '请提供恢复密钥或邮箱验证码'
                }).encode()
            
            # 更新密码
            self.db.update_user_password(
                user.id,
                new_password_hash,
                new_encrypted_master_key,
                new_master_key_salt
            )
            
            return PacketType.PASSWORD_RESET_RESPONSE, json.dumps({
                'success': True,
                'message': '密码重置成功'
            }).encode()
        except Exception as e:
            return PacketType.PASSWORD_RESET_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    # ============ 文件操作处理 ============
    
    def _require_auth(self, session: Session) -> Optional[Tuple[PacketType, bytes]]:
        """要求认证"""
        if not session.user_id:
            return PacketType.ERROR, json.dumps({
                'success': False,
                'error': '请先登录'
            }).encode()
        return None
    
    def _handle_file_list(self, session: Session, 
                          payload: bytes) -> Tuple[PacketType, bytes]:
        """处理文件列表请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            parent_id = data.get('parent_id')
            group_id = data.get('group_id')
            
            if group_id:
                # 验证群组成员资格
                if not self.db.is_group_member(group_id, session.user_id):
                    return PacketType.FILE_LIST_RESPONSE, json.dumps({
                        'success': False,
                        'error': '无权访问此群组'
                    }).encode()
                files = self.db.get_files(group_id=group_id, parent_id=parent_id)
            else:
                files = self.db.get_files(owner_id=session.user_id, parent_id=parent_id)
            
            # 将 bytes 转换为 hex 字符串以支持 JSON 序列化
            for f in files:
                if isinstance(f.get('encrypted_file_key'), bytes):
                    f['encrypted_file_key'] = f['encrypted_file_key'].hex()
            
            return PacketType.FILE_LIST_RESPONSE, json.dumps({
                'success': True,
                'files': files
            }).encode()
        except Exception as e:
            return PacketType.FILE_LIST_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_upload_start(self, session: Session, 
                             payload: bytes) -> Tuple[PacketType, bytes]:
        """处理上传开始请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            filename = data['filename']
            size = data['size']
            encrypted_file_key = bytes.fromhex(data['encrypted_file_key'])
            parent_id = data.get('parent_id')
            group_id = data.get('group_id')
            path = data.get('path', '/' + filename)
            
            # 生成存储路径
            storage_path = self.storage.generate_storage_path(
                user_id=session.user_id if not group_id else None,
                group_id=group_id
            )
            
            # 创建文件记录（owner_id 始终为上传者的 ID）
            file_id = self.db.create_file(
                owner_id=session.user_id,  # 始终记录上传者
                group_id=group_id,
                name=filename,
                path=path,
                storage_path=storage_path,
                size=size,
                encrypted_file_key=encrypted_file_key,
                is_folder=False,
                parent_id=parent_id
            )
            
            # 创建上传会话 - 直接写入临时文件，避免内存占用
            import tempfile
            upload_id = os.urandom(16).hex()
            
            # 创建临时文件用于接收上传数据
            temp_fd, temp_path = tempfile.mkstemp(suffix='.upload')
            temp_file = os.fdopen(temp_fd, 'wb')
            
            self._upload_sessions[upload_id] = {
                'file_id': file_id,
                'storage_path': storage_path,
                'received': 0,
                'total': size,
                'temp_file': temp_file,  # 临时文件对象
                'temp_path': temp_path,  # 临时文件路径
                'group_id': group_id,
                'filename': filename,
                'uploader_id': session.user_id
            }
            
            return PacketType.FILE_UPLOAD_START, json.dumps({
                'success': True,
                'upload_id': upload_id,
                'file_id': file_id
            }).encode()
        except Exception as e:
            return PacketType.FILE_UPLOAD_START, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_upload_data(self, session: Session, 
                            payload: bytes) -> Tuple[PacketType, bytes]:
        """处理上传数据"""
        try:
            # 提取 upload_id (前 32 字节是 hex 编码的 16 字节 ID)
            upload_id = payload[:32].decode('utf-8')
            data = payload[32:]
            
            upload = self._upload_sessions.get(upload_id)
            if not upload:
                return PacketType.FILE_UPLOAD_DATA, json.dumps({
                    'success': False,
                    'error': '上传会话不存在'
                }).encode()
            
            # 直接写入临时文件，不占用内存
            upload['temp_file'].write(data)
            upload['received'] += len(data)
            
            return PacketType.FILE_UPLOAD_DATA, json.dumps({
                'success': True,
                'received': upload['received']
            }).encode()
        except Exception as e:
            return PacketType.FILE_UPLOAD_DATA, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_upload_end(self, session: Session, 
                           payload: bytes) -> Tuple[PacketType, bytes]:
        """处理上传结束"""
        try:
            data = json.loads(payload.decode('utf-8'))
            upload_id = data['upload_id']
            
            upload = self._upload_sessions.pop(upload_id, None)
            if not upload:
                return PacketType.FILE_UPLOAD_END, json.dumps({
                    'success': False,
                    'error': '上传会话不存在'
                }).encode()
            
            # 关闭临时文件
            temp_file = upload['temp_file']
            temp_path = upload['temp_path']
            temp_file.close()
            
            # 移动临时文件到存储位置（使用流式复制避免内存占用）
            import shutil
            storage_full_path = str(self.storage.get_absolute_path(upload['storage_path']))
            os.makedirs(os.path.dirname(storage_full_path), exist_ok=True)
            shutil.move(temp_path, storage_full_path)
            
            # 如果是群组文件，为其他成员创建通知
            group_id = upload.get('group_id')
            if group_id:
                members = self.db.get_group_members(group_id)
                uploader_id = upload.get('uploader_id')
                filename = upload.get('filename')
                for member in members:
                    if member['id'] != uploader_id:
                        self.db.create_notification(
                            user_id=member['id'],
                            notification_type='new_file',
                            reference_id=upload['file_id'],
                            group_id=group_id,
                            message=f"群组有新文件: {filename}"
                        )
            
            return PacketType.FILE_UPLOAD_END, json.dumps({
                'success': True,
                'file_id': upload['file_id']
            }).encode()
        except Exception as e:
            return PacketType.FILE_UPLOAD_END, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_upload_cancel(self, session: Session, 
                              payload: bytes) -> Tuple[PacketType, bytes]:
        """处理上传取消"""
        try:
            data = json.loads(payload.decode('utf-8'))
            upload_id = data['upload_id']
            
            upload = self._upload_sessions.pop(upload_id, None)
            if upload:
                # 关闭并删除临时文件
                try:
                    upload['temp_file'].close()
                    os.unlink(upload['temp_path'])
                except:
                    pass
                
                # 删除数据库中的文件记录
                file_id = upload.get('file_id')
                if file_id:
                    self.db.delete_file(file_id)
            
            return PacketType.FILE_UPLOAD_CANCEL, json.dumps({
                'success': True
            }).encode()
        except Exception as e:
            return PacketType.FILE_UPLOAD_CANCEL, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_download_request(self, session: Session, 
                                 payload: bytes) -> Tuple[PacketType, bytes]:
        """处理下载请求 - 返回元数据，准备分块下载"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            file_id = data['file_id']
            
            file_info = self.db.get_file(file_id)
            if not file_info:
                return PacketType.FILE_DOWNLOAD_START, json.dumps({
                    'success': False,
                    'error': '文件不存在'
                }).encode()
            
            # 验证权限
            if file_info['group_id']:
                if not self.db.is_group_member(file_info['group_id'], session.user_id):
                    return PacketType.FILE_DOWNLOAD_START, json.dumps({
                        'success': False,
                        'error': '无权访问此文件'
                    }).encode()
            else:
                if file_info['owner_id'] and file_info['owner_id'] != session.user_id:
                    return PacketType.FILE_DOWNLOAD_START, json.dumps({
                        'success': False,
                        'error': '无权访问此文件'
                    }).encode()
            
            # 获取文件路径和大小（不读取到内存）
            storage_path = file_info['storage_path']
            full_path = str(self.storage.get_absolute_path(storage_path))
            
            if not os.path.exists(full_path):
                return PacketType.FILE_DOWNLOAD_START, json.dumps({
                    'success': False,
                    'error': '文件数据不存在'
                }).encode()
            
            file_size = os.path.getsize(full_path)
            
            # 创建下载会话 - 只存储文件路径，不加载数据
            import uuid
            download_id = str(uuid.uuid4())
            
            self._download_sessions[download_id] = {
                'file_id': file_id,
                'file_path': full_path,  # 存储文件路径字符串
                'file_handle': None,     # 延迟打开文件
                'offset': 0,
                'size': file_size
            }
            
            # 返回元数据（不包含文件数据）
            return PacketType.FILE_DOWNLOAD_START, json.dumps({
                'success': True,
                'download_id': download_id,
                'file_id': file_id,
                'filename': file_info['name'],
                'size': file_size,
                'encrypted_file_key': file_info['encrypted_file_key'].hex()
            }).encode()
        except Exception as e:
            return PacketType.FILE_DOWNLOAD_START, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_download_data(self, session: Session, 
                              payload: bytes) -> Tuple[PacketType, bytes]:
        """处理下载数据请求 - 从文件读取数据块"""
        try:
            data = json.loads(payload.decode('utf-8'))
            download_id = data['download_id']
            chunk_size = data.get('chunk_size', 256 * 1024)  # 默认256KB
            
            download = self._download_sessions.get(download_id)
            if not download:
                return PacketType.FILE_DOWNLOAD_DATA, json.dumps({
                    'success': False,
                    'error': '下载会话不存在'
                }).encode()
            
            # 延迟打开文件（第一次请求数据时打开）
            if download['file_handle'] is None:
                download['file_handle'] = open(download['file_path'], 'rb')
            
            file_handle = download['file_handle']
            total_size = download['size']
            
            # 从文件读取一块数据
            chunk = file_handle.read(chunk_size)
            download['offset'] += len(chunk)
            
            # 检查是否完成
            is_complete = download['offset'] >= total_size or len(chunk) == 0
            
            import base64
            
            response = {
                'success': True,
                'download_id': download_id,
                'offset': download['offset'] - len(chunk),
                'chunk_size': len(chunk),
                'is_complete': is_complete,
                'data': base64.b64encode(chunk).decode('ascii')
            }
            
            # 如果完成，关闭文件并清理会话
            if is_complete:
                file_handle.close()
                del self._download_sessions[download_id]
            
            return PacketType.FILE_DOWNLOAD_DATA, json.dumps(response).encode()
        except Exception as e:
            return PacketType.FILE_DOWNLOAD_DATA, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    
    def _handle_delete(self, session: Session, 
                       payload: bytes) -> Tuple[PacketType, bytes]:
        """处理删除请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            file_id = data['file_id']
            
            file_info = self.db.get_file(file_id)
            if not file_info:
                return PacketType.FILE_DELETE_RESPONSE, json.dumps({
                    'success': False,
                    'error': '文件不存在'
                }).encode()
            
            # 验证权限
            # 群组文件：任何群组成员可删除
            # 个人文件：只有所有者可删除
            if file_info['group_id']:
                if not self.db.is_group_member(file_info['group_id'], session.user_id):
                    return PacketType.FILE_DELETE_RESPONSE, json.dumps({
                        'success': False,
                        'error': '无权删除此文件'
                    }).encode()
            else:
                if file_info['owner_id'] and file_info['owner_id'] != session.user_id:
                    return PacketType.FILE_DELETE_RESPONSE, json.dumps({
                        'success': False,
                        'error': '无权删除此文件'
                    }).encode()
            
            # 删除物理文件
            if not file_info['is_folder']:
                self.storage.delete_file(file_info['storage_path'])
            
            # 删除数据库记录
            self.db.delete_file(file_id)
            
            return PacketType.FILE_DELETE_RESPONSE, json.dumps({
                'success': True
            }).encode()
        except Exception as e:
            return PacketType.FILE_DELETE_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_rename(self, session: Session, 
                       payload: bytes) -> Tuple[PacketType, bytes]:
        """处理重命名请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            file_id = data['file_id']
            new_name = data['new_name']
            
            file_info = self.db.get_file(file_id)
            if not file_info:
                return PacketType.FILE_RENAME_RESPONSE, json.dumps({
                    'success': False,
                    'error': '文件不存在'
                }).encode()
            
            # 验证权限
            # 群组文件：任何群组成员可重命名
            # 个人文件：只有所有者可重命名
            if file_info['group_id']:
                if not self.db.is_group_member(file_info['group_id'], session.user_id):
                    return PacketType.FILE_RENAME_RESPONSE, json.dumps({
                        'success': False,
                        'error': '无权修改此文件'
                    }).encode()
            else:
                if file_info['owner_id'] and file_info['owner_id'] != session.user_id:
                    return PacketType.FILE_RENAME_RESPONSE, json.dumps({
                        'success': False,
                        'error': '无权修改此文件'
                    }).encode()
            
            self.db.update_file(file_id, name=new_name)
            
            return PacketType.FILE_RENAME_RESPONSE, json.dumps({
                'success': True
            }).encode()
        except Exception as e:
            return PacketType.FILE_RENAME_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_create_folder(self, session: Session, 
                              payload: bytes) -> Tuple[PacketType, bytes]:
        """处理创建文件夹请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            name = data['name']
            parent_id = data.get('parent_id')
            group_id = data.get('group_id')
            path = data.get('path', '/' + name)
            
            folder_id = self.db.create_file(
                owner_id=session.user_id if not group_id else None,
                group_id=group_id,
                name=name,
                path=path,
                storage_path='',
                size=0,
                encrypted_file_key=b'',
                is_folder=True,
                parent_id=parent_id
            )
            
            return PacketType.FOLDER_CREATE_RESPONSE, json.dumps({
                'success': True,
                'folder_id': folder_id
            }).encode()
        except Exception as e:
            return PacketType.FOLDER_CREATE_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    # ============ 群组操作处理 ============
    
    def _handle_group_create(self, session: Session, 
                             payload: bytes) -> Tuple[PacketType, bytes]:
        """处理创建群组请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            name = data['name']
            encrypted_group_key_hex = data.get('encrypted_group_key', '')
            encrypted_group_key = bytes.fromhex(encrypted_group_key_hex) if encrypted_group_key_hex else b''
            
            group_id = self.db.create_group(name, session.user_id, encrypted_group_key)
            
            return PacketType.GROUP_CREATE_RESPONSE, json.dumps({
                'success': True,
                'group_id': group_id
            }).encode()
        except Exception as e:
            return PacketType.GROUP_CREATE_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_group_list(self, session: Session, 
                           payload: bytes) -> Tuple[PacketType, bytes]:
        """处理群组列表请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            groups = self.db.get_user_groups(session.user_id)
            invitations = self.db.get_user_invitations(session.user_id)
            
            # 将 bytes 转换为 hex 字符串以支持 JSON 序列化
            for inv in invitations:
                if isinstance(inv.get('encrypted_group_key'), bytes):
                    inv['encrypted_group_key'] = inv['encrypted_group_key'].hex()
            
            return PacketType.GROUP_LIST_RESPONSE, json.dumps({
                'success': True,
                'groups': groups,
                'invitations': invitations
            }).encode()
        except Exception as e:
            return PacketType.GROUP_LIST_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_group_invite(self, session: Session, 
                             payload: bytes) -> Tuple[PacketType, bytes]:
        """处理群组邀请请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            group_id = data['group_id']
            invitee_username = data['username']
            encrypted_group_key = bytes.fromhex(data['encrypted_group_key'])
            
            # 验证邀请人是群组成员
            if not self.db.is_group_member(group_id, session.user_id):
                return PacketType.GROUP_INVITE_RESPONSE, json.dumps({
                    'success': False,
                    'error': '您不是此群组成员'
                }).encode()
            
            # 获取被邀请人
            invitee = self.db.get_user_by_username(invitee_username)
            if not invitee:
                return PacketType.GROUP_INVITE_RESPONSE, json.dumps({
                    'success': False,
                    'error': '用户不存在'
                }).encode()
            
            # 检查是否已是成员
            if self.db.is_group_member(group_id, invitee.id):
                return PacketType.GROUP_INVITE_RESPONSE, json.dumps({
                    'success': False,
                    'error': '该用户已是群组成员'
                }).encode()
            
            # 创建邀请
            invitation_id = self.db.create_invitation(
                group_id, session.user_id, invitee.id, encrypted_group_key
            )
            
            # 创建通知
            group = self.db.get_group(group_id)
            self.db.create_notification(
                user_id=invitee.id,
                notification_type='invitation',
                reference_id=invitation_id,
                group_id=group_id,
                message=f"您被邀请加入群组: {group['name'] if group else '未知群组'}"
            )
            
            return PacketType.GROUP_INVITE_RESPONSE, json.dumps({
                'success': True,
                'invitation_id': invitation_id
            }).encode()
        except Exception as e:
            return PacketType.GROUP_INVITE_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_group_join(self, session: Session, 
                           payload: bytes) -> Tuple[PacketType, bytes]:
        """处理接受/拒绝邀请请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            invitation_id = data['invitation_id']
            accept = data.get('accept', True)
            
            if accept:
                result = self.db.accept_invitation(invitation_id, session.user_id)
                if result:
                    return PacketType.GROUP_JOIN_RESPONSE, json.dumps({
                        'success': True,
                        'group_id': result['group_id']
                    }).encode()
            else:
                self.db.reject_invitation(invitation_id, session.user_id)
                return PacketType.GROUP_JOIN_RESPONSE, json.dumps({
                    'success': True
                }).encode()
            
            return PacketType.GROUP_JOIN_RESPONSE, json.dumps({
                'success': False,
                'error': '邀请不存在或已处理'
            }).encode()
        except Exception as e:
            return PacketType.GROUP_JOIN_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_group_leave(self, session: Session, 
                            payload: bytes) -> Tuple[PacketType, bytes]:
        """处理退出群组请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            group_id = data['group_id']
            
            group = self.db.get_group(group_id)
            if not group:
                return PacketType.GROUP_LEAVE_RESPONSE, json.dumps({
                    'success': False,
                    'error': '群组不存在'
                }).encode()
            
            # 群主不能退出，只能解散
            if group['owner_id'] == session.user_id:
                self.db.delete_group(group_id)
            else:
                self.db.remove_group_member(group_id, session.user_id)
            
            return PacketType.GROUP_LEAVE_RESPONSE, json.dumps({
                'success': True
            }).encode()
        except Exception as e:
            return PacketType.GROUP_LEAVE_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_group_key(self, session: Session, 
                          payload: bytes) -> Tuple[PacketType, bytes]:
        """处理获取群组密钥请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            group_id = data['group_id']
            
            # 获取成员的加密群组密钥
            members = self.db.get_group_members(group_id)
            member = next(
                (m for m in members if m['id'] == session.user_id), 
                None
            )
            
            if not member:
                return PacketType.GROUP_KEY_RESPONSE, json.dumps({
                    'success': False,
                    'error': '您不是此群组成员'
                }).encode()
            
            # 获取所有成员的公钥（用于加密共享文件的密钥）
            member_keys = [
                {'user_id': m['id'], 'public_key': m['public_key'].hex()}
                for m in members
            ]
            
            # 获取当前用户的加密群组密钥
            encrypted_group_key = member.get('encrypted_group_key')
            
            return PacketType.GROUP_KEY_RESPONSE, json.dumps({
                'success': True,
                'members': member_keys,
                'encrypted_group_key': encrypted_group_key.hex() if encrypted_group_key else None
            }).encode()
        except Exception as e:
            return PacketType.GROUP_KEY_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_user_public_key(self, session: Session, 
                                payload: bytes) -> Tuple[PacketType, bytes]:
        """处理获取用户公钥请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            username = data['username']
            
            user = self.db.get_user_by_username(username)
            if not user:
                return PacketType.USER_PUBLIC_KEY_RESPONSE, json.dumps({
                    'success': False,
                    'error': '用户不存在'
                }).encode()
            
            return PacketType.USER_PUBLIC_KEY_RESPONSE, json.dumps({
                'success': True,
                'user_id': user.id,
                'username': user.username,
                'public_key': user.public_key.hex()
            }).encode()
        except Exception as e:
            return PacketType.USER_PUBLIC_KEY_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_group_members(self, session: Session, 
                               payload: bytes) -> Tuple[PacketType, bytes]:
        """处理获取群组成员请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            group_id = data['group_id']
            
            # 检查用户是否为群组成员
            if not self.db.is_group_member(group_id, session.user_id):
                return PacketType.GROUP_MEMBERS_RESPONSE, json.dumps({
                    'success': False,
                    'error': '您不是此群组成员'
                }).encode()
            
            # 获取成员信息
            members = self.db.get_group_members(group_id)
            member_list = []
            for m in members:
                member_list.append({
                    'id': m['id'],
                    'username': m['username'],
                    'email': m.get('email', ''),
                    'role': m['role']
                })
            
            return PacketType.GROUP_MEMBERS_RESPONSE, json.dumps({
                'success': True,
                'members': member_list
            }).encode()
            
        except Exception as e:
            return PacketType.GROUP_MEMBERS_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_notification_count(self, session: Session, 
                                   payload: bytes) -> Tuple[PacketType, bytes]:
        """处理获取通知计数请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            counts = self.db.get_unread_notification_counts(session.user_id)
            return PacketType.NOTIFICATION_COUNT_RESPONSE, json.dumps({
                'success': True,
                'invitation_count': counts['invitation_count'],
                'file_count': counts['file_count'],
                'group_file_counts': counts['group_file_counts']
            }).encode()
        except Exception as e:
            return PacketType.NOTIFICATION_COUNT_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
    
    def _handle_notification_read(self, session: Session, 
                                  payload: bytes) -> Tuple[PacketType, bytes]:
        """处理标记通知已读请求"""
        auth_error = self._require_auth(session)
        if auth_error:
            return auth_error
        
        try:
            data = json.loads(payload.decode('utf-8'))
            notification_type = data.get('type')
            group_id = data.get('group_id')
            
            self.db.mark_notifications_read(session.user_id, notification_type, group_id)
            
            return PacketType.NOTIFICATION_READ_RESPONSE, json.dumps({
                'success': True
            }).encode()
        except Exception as e:
            return PacketType.NOTIFICATION_READ_RESPONSE, json.dumps({
                'success': False,
                'error': str(e)
            }).encode()
