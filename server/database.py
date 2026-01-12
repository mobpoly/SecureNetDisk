"""
数据库管理模块
使用 SQLite 存储用户、群组和文件元数据
"""

import sqlite3
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from auth.user import User


class Database:
    """SQLite 数据库管理器"""
    
    def __init__(self, db_path: Path):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._local = threading.local()
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def cursor(self):
        """获取数据库游标的上下文管理器"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _init_database(self):
        """初始化数据库表"""
        with self.cursor() as cur:
            # 用户表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash BLOB NOT NULL,
                    public_key BLOB NOT NULL,
                    encrypted_private_key BLOB NOT NULL,
                    private_key_salt BLOB,
                    encrypted_master_key BLOB NOT NULL,
                    master_key_salt BLOB NOT NULL,
                    recovery_key_encrypted BLOB NOT NULL,
                    recovery_key_salt BLOB NOT NULL,
                    recovery_key_hash BLOB NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_login TEXT
                )
            ''')
            
            # 群组表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    owner_id INTEGER NOT NULL,
                    encrypted_group_key BLOB,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (owner_id) REFERENCES users(id)
                )
            ''')
            
            # 群组成员表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS group_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    encrypted_group_key BLOB NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at TEXT NOT NULL,
                    FOREIGN KEY (group_id) REFERENCES groups(id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(group_id, user_id)
                )
            ''')
            
            # 群组邀请表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS group_invitations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    inviter_id INTEGER NOT NULL,
                    invitee_id INTEGER NOT NULL,
                    encrypted_group_key BLOB NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (group_id) REFERENCES groups(id),
                    FOREIGN KEY (inviter_id) REFERENCES users(id),
                    FOREIGN KEY (invitee_id) REFERENCES users(id)
                )
            ''')
            
            # 文件元数据表
            cur.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER,
                    group_id INTEGER,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    storage_path TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    encrypted_file_key BLOB NOT NULL,
                    is_folder INTEGER DEFAULT 0,
                    parent_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (owner_id) REFERENCES users(id),
                    FOREIGN KEY (group_id) REFERENCES groups(id),
                    FOREIGN KEY (parent_id) REFERENCES files(id)
                )
            ''')
            
            # 创建索引
            cur.execute('CREATE INDEX IF NOT EXISTS idx_files_owner ON files(owner_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_files_group ON files(group_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_files_parent ON files(parent_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id)')
    
    # ============ 用户操作 ============
    
    def create_user(self, user: User) -> int:
        """创建用户"""
        with self.cursor() as cur:
            cur.execute('''
                INSERT INTO users (
                    username, email, password_hash, public_key,
                    encrypted_private_key, private_key_salt,
                    encrypted_master_key, master_key_salt,
                    recovery_key_encrypted, recovery_key_salt, recovery_key_hash,
                    is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user.username, user.email, user.password_hash, user.public_key,
                user.encrypted_private_key, user.private_key_salt,
                user.encrypted_master_key, user.master_key_salt,
                user.recovery_key_encrypted, user.recovery_key_salt, user.recovery_key_hash,
                1, datetime.now().isoformat()
            ))
            return cur.lastrowid
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """通过 ID 获取用户"""
        with self.cursor() as cur:
            cur.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cur.fetchone()
            return self._row_to_user(row) if row else None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        with self.cursor() as cur:
            cur.execute('SELECT * FROM users WHERE username = ?', (username,))
            row = cur.fetchone()
            return self._row_to_user(row) if row else None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """通过 Email 获取用户"""
        with self.cursor() as cur:
            cur.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cur.fetchone()
            return self._row_to_user(row) if row else None
    
    def update_user_password(self, user_id: int, password_hash: bytes,
                             encrypted_master_key: bytes, master_key_salt: bytes):
        """更新用户密码"""
        with self.cursor() as cur:
            cur.execute('''
                UPDATE users SET 
                    password_hash = ?,
                    encrypted_master_key = ?,
                    master_key_salt = ?
                WHERE id = ?
            ''', (password_hash, encrypted_master_key, master_key_salt, user_id))
    
    def update_last_login(self, user_id: int):
        """更新最后登录时间"""
        with self.cursor() as cur:
            cur.execute(
                'UPDATE users SET last_login = ? WHERE id = ?',
                (datetime.now().isoformat(), user_id)
            )
    
    def _row_to_user(self, row: sqlite3.Row) -> User:
        """将数据库行转换为 User 对象"""
        return User(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            password_hash=row['password_hash'],
            public_key=row['public_key'],
            encrypted_private_key=row['encrypted_private_key'],
            private_key_salt=row['private_key_salt'] or b'',
            encrypted_master_key=row['encrypted_master_key'],
            master_key_salt=row['master_key_salt'],
            recovery_key_encrypted=row['recovery_key_encrypted'],
            recovery_key_salt=row['recovery_key_salt'],
            recovery_key_hash=row['recovery_key_hash'],
            is_active=bool(row['is_active']),
            created_at=datetime.fromisoformat(row['created_at']),
            last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None
        )
    
    # ============ 群组操作 ============
    
    def create_group(self, name: str, owner_id: int) -> int:
        """创建群组"""
        with self.cursor() as cur:
            cur.execute('''
                INSERT INTO groups (name, owner_id, created_at)
                VALUES (?, ?, ?)
            ''', (name, owner_id, datetime.now().isoformat()))
            group_id = cur.lastrowid
            
            # 群主自动加入群组
            cur.execute('''
                INSERT INTO group_members (group_id, user_id, encrypted_group_key, role, joined_at)
                VALUES (?, ?, ?, 'owner', ?)
            ''', (group_id, owner_id, b'', datetime.now().isoformat()))
            
            return group_id
    
    def get_group(self, group_id: int) -> Optional[Dict]:
        """获取群组信息"""
        with self.cursor() as cur:
            cur.execute('SELECT * FROM groups WHERE id = ?', (group_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_user_groups(self, user_id: int) -> List[Dict]:
        """获取用户加入的所有群组"""
        with self.cursor() as cur:
            cur.execute('''
                SELECT g.*, gm.role, gm.encrypted_group_key
                FROM groups g
                JOIN group_members gm ON g.id = gm.group_id
                WHERE gm.user_id = ?
            ''', (user_id,))
            return [dict(row) for row in cur.fetchall()]
    
    def get_group_members(self, group_id: int) -> List[Dict]:
        """获取群组成员列表"""
        with self.cursor() as cur:
            cur.execute('''
                SELECT u.id, u.username, u.email, u.public_key, gm.role, gm.joined_at
                FROM users u
                JOIN group_members gm ON u.id = gm.user_id
                WHERE gm.group_id = ?
            ''', (group_id,))
            return [dict(row) for row in cur.fetchall()]
    
    def add_group_member(self, group_id: int, user_id: int, encrypted_group_key: bytes):
        """添加群组成员"""
        with self.cursor() as cur:
            cur.execute('''
                INSERT INTO group_members (group_id, user_id, encrypted_group_key, role, joined_at)
                VALUES (?, ?, ?, 'member', ?)
            ''', (group_id, user_id, encrypted_group_key, datetime.now().isoformat()))
    
    def update_member_group_key(self, group_id: int, user_id: int, encrypted_group_key: bytes):
        """更新成员的加密群组密钥"""
        with self.cursor() as cur:
            cur.execute('''
                UPDATE group_members 
                SET encrypted_group_key = ?
                WHERE group_id = ? AND user_id = ?
            ''', (encrypted_group_key, group_id, user_id))
    
    def is_group_member(self, group_id: int, user_id: int) -> bool:
        """检查用户是否为群组成员"""
        with self.cursor() as cur:
            cur.execute('''
                SELECT 1 FROM group_members WHERE group_id = ? AND user_id = ?
            ''', (group_id, user_id))
            return cur.fetchone() is not None
    
    def remove_group_member(self, group_id: int, user_id: int):
        """移除群组成员"""
        with self.cursor() as cur:
            cur.execute('''
                DELETE FROM group_members WHERE group_id = ? AND user_id = ?
            ''', (group_id, user_id))
    
    def delete_group(self, group_id: int):
        """删除群组"""
        with self.cursor() as cur:
            cur.execute('DELETE FROM group_members WHERE group_id = ?', (group_id,))
            cur.execute('DELETE FROM files WHERE group_id = ?', (group_id,))
            cur.execute('DELETE FROM groups WHERE id = ?', (group_id,))
    
    # ============ 群组邀请操作 ============
    
    def create_invitation(self, group_id: int, inviter_id: int, 
                          invitee_id: int, encrypted_group_key: bytes) -> int:
        """创建群组邀请"""
        with self.cursor() as cur:
            cur.execute('''
                INSERT INTO group_invitations (group_id, inviter_id, invitee_id, encrypted_group_key, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
            ''', (group_id, inviter_id, invitee_id, encrypted_group_key, datetime.now().isoformat()))
            return cur.lastrowid
    
    def get_user_invitations(self, user_id: int) -> List[Dict]:
        """获取用户的待处理邀请"""
        with self.cursor() as cur:
            cur.execute('''
                SELECT gi.*, g.name as group_name, u.username as inviter_name
                FROM group_invitations gi
                JOIN groups g ON gi.group_id = g.id
                JOIN users u ON gi.inviter_id = u.id
                WHERE gi.invitee_id = ? AND gi.status = 'pending'
            ''', (user_id,))
            return [dict(row) for row in cur.fetchall()]
    
    def accept_invitation(self, invitation_id: int, user_id: int) -> Optional[Dict]:
        """接受邀请"""
        with self.cursor() as cur:
            cur.execute('''
                SELECT * FROM group_invitations WHERE id = ? AND invitee_id = ? AND status = 'pending'
            ''', (invitation_id, user_id))
            row = cur.fetchone()
            if not row:
                return None
            
            invitation = dict(row)
            
            # 更新邀请状态
            cur.execute('''
                UPDATE group_invitations SET status = 'accepted' WHERE id = ?
            ''', (invitation_id,))
            
            # 添加为群组成员
            cur.execute('''
                INSERT INTO group_members (group_id, user_id, encrypted_group_key, role, joined_at)
                VALUES (?, ?, ?, 'member', ?)
            ''', (invitation['group_id'], user_id, invitation['encrypted_group_key'], 
                  datetime.now().isoformat()))
            
            return invitation
    
    def reject_invitation(self, invitation_id: int, user_id: int) -> bool:
        """拒绝邀请"""
        with self.cursor() as cur:
            cur.execute('''
                UPDATE group_invitations SET status = 'rejected' 
                WHERE id = ? AND invitee_id = ? AND status = 'pending'
            ''', (invitation_id, user_id))
            return cur.rowcount > 0
    
    # ============ 文件操作 ============
    
    def create_file(self, owner_id: int, group_id: int, name: str, path: str,
                    storage_path: str, size: int, encrypted_file_key: bytes,
                    is_folder: bool = False, parent_id: int = None) -> int:
        """创建文件记录"""
        now = datetime.now().isoformat()
        with self.cursor() as cur:
            cur.execute('''
                INSERT INTO files (
                    owner_id, group_id, name, path, storage_path, size,
                    encrypted_file_key, is_folder, parent_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (owner_id, group_id, name, path, storage_path, size,
                  encrypted_file_key, int(is_folder), parent_id, now, now))
            return cur.lastrowid
    
    def get_files(self, owner_id: int = None, group_id: int = None, 
                  parent_id: int = None) -> List[Dict]:
        """获取文件列表"""
        with self.cursor() as cur:
            conditions = []
            params = []
            
            if owner_id is not None:
                conditions.append('f.owner_id = ?')
                params.append(owner_id)
            if group_id is not None:
                conditions.append('f.group_id = ?')
                params.append(group_id)
            
            # 处理 parent_id (None 代表根目录)
            if parent_id is None:
                conditions.append('f.parent_id IS NULL')
            else:
                conditions.append('f.parent_id = ?')
                params.append(parent_id)
            
            where_clause = ' AND '.join(conditions) if conditions else '1=1'
            
            cur.execute(f'''
                SELECT f.*, u.username as uploader_name 
                FROM files f
                LEFT JOIN users u ON f.owner_id = u.id
                WHERE {where_clause} 
                ORDER BY f.is_folder DESC, f.name
            ''', params)
            return [dict(row) for row in cur.fetchall()]
    
    def get_file(self, file_id: int) -> Optional[Dict]:
        """获取单个文件信息"""
        with self.cursor() as cur:
            cur.execute('SELECT * FROM files WHERE id = ?', (file_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def get_file_by_path(self, path: str, owner_id: int = None, 
                         group_id: int = None) -> Optional[Dict]:
        """通过路径获取文件"""
        with self.cursor() as cur:
            if owner_id:
                cur.execute('''
                    SELECT * FROM files WHERE path = ? AND owner_id = ?
                ''', (path, owner_id))
            elif group_id:
                cur.execute('''
                    SELECT * FROM files WHERE path = ? AND group_id = ?
                ''', (path, group_id))
            else:
                return None
            row = cur.fetchone()
            return dict(row) if row else None
    
    def update_file(self, file_id: int, **kwargs):
        """更新文件信息"""
        if not kwargs:
            return
        
        kwargs['updated_at'] = datetime.now().isoformat()
        
        with self.cursor() as cur:
            set_clause = ', '.join(f'{k} = ?' for k in kwargs.keys())
            values = list(kwargs.values()) + [file_id]
            cur.execute(f'UPDATE files SET {set_clause} WHERE id = ?', values)
    
    def delete_file(self, file_id: int):
        """删除文件"""
        with self.cursor() as cur:
            # 递归删除子文件
            cur.execute('SELECT id FROM files WHERE parent_id = ?', (file_id,))
            children = cur.fetchall()
            for child in children:
                self.delete_file(child['id'])
            
            cur.execute('DELETE FROM files WHERE id = ?', (file_id,))
    
    def search_files(self, query: str, owner_id: int = None, 
                     group_id: int = None) -> List[Dict]:
        """搜索文件"""
        with self.cursor() as cur:
            conditions = ['name LIKE ?']
            params = [f'%{query}%']
            
            if owner_id:
                conditions.append('owner_id = ?')
                params.append(owner_id)
            if group_id:
                conditions.append('group_id = ?')
                params.append(group_id)
            
            where_clause = ' AND '.join(conditions)
            cur.execute(f'''
                SELECT * FROM files WHERE {where_clause} ORDER BY name
            ''', params)
            return [dict(row) for row in cur.fetchall()]
