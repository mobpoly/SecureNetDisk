"""
会话管理模块
管理已建立的安全会话
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Set
from collections import OrderedDict


@dataclass
class Session:
    """安全会话"""
    
    session_id: str
    client_key: bytes          # 客户端->服务端 加密密钥
    server_key: bytes          # 服务端->客户端 加密密钥
    hmac_key: bytes            # HMAC 认证密钥
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    
    # 防重放攻击
    client_sequence: int = 0   # 客户端发送的最大序列号
    server_sequence: int = 0   # 服务端发送的序列号
    seen_sequences: Set[int] = field(default_factory=set)
    
    # 用户信息（认证后填充）
    user_id: Optional[int] = None
    username: Optional[str] = None
    
    # 会话配置
    timeout: int = 3600        # 会话超时时间（秒）
    max_seen_sequences: int = 10000  # 最大保存的序列号数量
    
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return time.time() - self.last_activity > self.timeout
    
    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = time.time()
    
    def validate_sequence(self, sequence: int, is_client: bool = True) -> bool:
        """
        验证序列号（防重放攻击）
        
        Args:
            sequence: 接收到的序列号
            is_client: 是否来自客户端
            
        Returns:
            序列号是否有效
        """
        # 检查是否已见过此序列号
        if sequence in self.seen_sequences:
            return False
        
        # 检查序列号是否过小（允许一定的乱序）
        current_max = self.client_sequence if is_client else self.server_sequence
        if sequence < current_max - 1000:  # 允许 1000 的窗口
            return False
        
        # 记录序列号
        self.seen_sequences.add(sequence)
        
        # 更新最大序列号
        if is_client:
            self.client_sequence = max(self.client_sequence, sequence)
        else:
            self.server_sequence = max(self.server_sequence, sequence)
        
        # 清理过多的历史序列号
        if len(self.seen_sequences) > self.max_seen_sequences:
            min_seq = min(self.client_sequence, self.server_sequence) - 1000
            self.seen_sequences = {s for s in self.seen_sequences if s > min_seq}
        
        return True
    
    def next_server_sequence(self) -> int:
        """获取下一个服务端序列号"""
        self.server_sequence += 1
        return self.server_sequence
    
    def validate_timestamp(self, timestamp: int, max_drift: int = 300000) -> bool:
        """
        验证时间戳（防重放攻击）
        
        Args:
            timestamp: 消息时间戳（毫秒）
            max_drift: 最大允许的时间偏差（毫秒）
            
        Returns:
            时间戳是否有效
        """
        current_time = int(time.time() * 1000)
        return abs(current_time - timestamp) <= max_drift


class SessionManager:
    """会话管理器"""
    
    def __init__(self, max_sessions: int = 10000, cleanup_interval: int = 60):
        """
        初始化会话管理器
        
        Args:
            max_sessions: 最大会话数
            cleanup_interval: 清理间隔（秒）
        """
        self._sessions: OrderedDict[str, Session] = OrderedDict()
        self._user_sessions: Dict[int, Set[str]] = {}  # user_id -> session_ids
        self._max_sessions = max_sessions
        self._lock = threading.RLock()
        
        # 启动清理线程
        self._cleanup_interval = cleanup_interval
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def create_session(self, session_id: str, keys: dict) -> Session:
        """
        创建新会话
        
        Args:
            session_id: 会话 ID
            keys: 包含 client_key, server_key, hmac_key 的字典
            
        Returns:
            新创建的 Session 对象
        """
        with self._lock:
            # 如果达到最大会话数，移除最旧的会话
            while len(self._sessions) >= self._max_sessions:
                oldest_id = next(iter(self._sessions))
                self.remove_session(oldest_id)
            
            session = Session(
                session_id=session_id,
                client_key=keys['client_key'],
                server_key=keys['server_key'],
                hmac_key=keys['hmac_key']
            )
            self._sessions[session_id] = session
            return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            Session 对象，不存在或已过期返回 None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                if session.is_expired():
                    self.remove_session(session_id)
                    return None
                session.update_activity()
                # 移动到末尾（LRU）
                self._sessions.move_to_end(session_id)
            return session
    
    def remove_session(self, session_id: str):
        """
        移除会话
        
        Args:
            session_id: 会话 ID
        """
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session and session.user_id:
                user_sessions = self._user_sessions.get(session.user_id, set())
                user_sessions.discard(session_id)
                if not user_sessions:
                    self._user_sessions.pop(session.user_id, None)
    
    def bind_user(self, session_id: str, user_id: int, username: str):
        """
        绑定用户到会话
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            username: 用户名
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.user_id = user_id
                session.username = username
                
                if user_id not in self._user_sessions:
                    self._user_sessions[user_id] = set()
                self._user_sessions[user_id].add(session_id)
    
    def get_user_sessions(self, user_id: int) -> list[Session]:
        """
        获取用户的所有会话
        
        Args:
            user_id: 用户 ID
            
        Returns:
            用户的所有活跃会话
        """
        with self._lock:
            session_ids = self._user_sessions.get(user_id, set())
            sessions = []
            for sid in list(session_ids):
                session = self.get_session(sid)
                if session:
                    sessions.append(session)
            return sessions
    
    def _cleanup_loop(self):
        """定期清理过期会话"""
        while self._running:
            time.sleep(self._cleanup_interval)
            self._cleanup_expired()
    
    def _cleanup_expired(self):
        """清理所有过期会话"""
        with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired()
            ]
            for sid in expired:
                self.remove_session(sid)
    
    def shutdown(self):
        """关闭会话管理器"""
        self._running = False
    
    @property
    def active_session_count(self) -> int:
        """活跃会话数"""
        with self._lock:
            return len(self._sessions)
