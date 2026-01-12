"""
用户模型
定义用户数据结构
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class User:
    """用户模型"""
    
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    password_hash: bytes = b""
    
    # RSA 密钥对
    public_key: bytes = b""              # 公钥（明文存储）
    encrypted_private_key: bytes = b""    # 私钥（用主密钥加密后存储）
    private_key_salt: bytes = b""         # 私钥加密盐值
    
    # 主密钥（用于加密用户数据）
    encrypted_master_key: bytes = b""     # 主密钥（用密码派生密钥加密）
    master_key_salt: bytes = b""          # 主密钥加密盐值
    
    # Email 恢复凭证
    recovery_key_encrypted: bytes = b""   # 主密钥（用恢复密钥加密）
    recovery_key_salt: bytes = b""        # 恢复密钥盐值
    recovery_key_hash: bytes = b""        # 恢复密钥哈希（用于验证）
    
    # 账户状态
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典（用于数据库存储）"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'public_key': self.public_key,
            'encrypted_private_key': self.encrypted_private_key,
            'private_key_salt': self.private_key_salt,
            'encrypted_master_key': self.encrypted_master_key,
            'master_key_salt': self.master_key_salt,
            'recovery_key_encrypted': self.recovery_key_encrypted,
            'recovery_key_salt': self.recovery_key_salt,
            'recovery_key_hash': self.recovery_key_hash,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """从字典创建用户对象"""
        created_at = data.get('created_at')
        last_login = data.get('last_login')
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if isinstance(last_login, str):
            last_login = datetime.fromisoformat(last_login)
        
        return cls(
            id=data.get('id'),
            username=data.get('username', ''),
            email=data.get('email', ''),
            password_hash=data.get('password_hash', b''),
            public_key=data.get('public_key', b''),
            encrypted_private_key=data.get('encrypted_private_key', b''),
            private_key_salt=data.get('private_key_salt', b''),
            encrypted_master_key=data.get('encrypted_master_key', b''),
            master_key_salt=data.get('master_key_salt', b''),
            recovery_key_encrypted=data.get('recovery_key_encrypted', b''),
            recovery_key_salt=data.get('recovery_key_salt', b''),
            recovery_key_hash=data.get('recovery_key_hash', b''),
            is_active=data.get('is_active', True),
            created_at=created_at or datetime.now(),
            last_login=last_login
        )


@dataclass
class UserCredentials:
    """用户凭据（登录时使用）"""
    username: str = ""
    password: str = ""
    email: str = ""
    verification_code: str = ""
    login_type: str = "password"  # "password" or "email"


@dataclass
class RegistrationData:
    """注册数据"""
    username: str
    email: str
    password: str
    
    # 客户端生成的密钥数据
    public_key: bytes = b""
    encrypted_private_key: bytes = b""
    private_key_salt: bytes = b""
    encrypted_master_key: bytes = b""
    master_key_salt: bytes = b""
    recovery_key_encrypted: bytes = b""
    recovery_key_salt: bytes = b""
    recovery_key_hash: bytes = b""
