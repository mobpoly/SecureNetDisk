"""
群组管理模块
客户端群组操作
"""

from typing import List, Dict, Optional
from dataclasses import dataclass

from client.network import NetworkClient
from client.key_manager import KeyManager
from .group_key import GroupKeyManager


@dataclass
class Group:
    """群组信息"""
    id: int
    name: str
    owner_id: int
    role: str  # 'owner' or 'member'


@dataclass
class Invitation:
    """群组邀请"""
    id: int
    group_id: int
    group_name: str
    inviter_name: str
    encrypted_group_key: bytes


class GroupManager:
    """群组管理器"""
    
    def __init__(self, network: NetworkClient, key_manager: KeyManager):
        """
        初始化群组管理器
        
        Args:
            network: 网络客户端
            key_manager: 密钥管理器
        """
        self.network = network
        self.key_manager = key_manager
        self.group_key_manager = GroupKeyManager(key_manager)
        self.groups: List[Group] = []
        self.invitations: List[Invitation] = []
    
    def refresh_groups(self) -> bool:
        """
        刷新群组列表
        
        Returns:
            是否成功
        """
        result = self.network.get_groups()
        if not result.get('success'):
            return False
        
        # 解析群组
        self.groups = []
        for g in result.get('groups', []):
            self.groups.append(Group(
                id=g['id'],
                name=g['name'],
                owner_id=g['owner_id'],
                role=g.get('role', 'member')
            ))
            
            # 解密群组密钥
            encrypted_key = bytes.fromhex(g.get('encrypted_group_key', '')) if g.get('encrypted_group_key') else b''
            if encrypted_key:
                try:
                    group_key = self.key_manager.decrypt_for_me(encrypted_key)
                    self.key_manager.set_group_key(g['id'], group_key)
                except Exception:
                    pass
        
        # 解析邀请
        self.invitations = []
        for inv in result.get('invitations', []):
            self.invitations.append(Invitation(
                id=inv['id'],
                group_id=inv['group_id'],
                group_name=inv['group_name'],
                inviter_name=inv['inviter_name'],
                encrypted_group_key=bytes.fromhex(inv.get('encrypted_group_key', '')) if inv.get('encrypted_group_key') else b''
            ))
        
        return True
    
    def create_group(self, name: str) -> Optional[int]:
        """
        创建群组
        
        Args:
            name: 群组名称
            
        Returns:
            群组 ID，失败返回 None
        """
        result = self.network.create_group(name)
        if result.get('success'):
            group_id = result['group_id']
            
            # 生成群组密钥
            group_key = self.key_manager.generate_group_key()
            self.key_manager.set_group_key(group_id, group_key)
            
            # 刷新列表
            self.refresh_groups()
            
            return group_id
        return None
    
    def invite_user(self, group_id: int, username: str, 
                    user_public_key: bytes) -> bool:
        """
        邀请用户加入群组
        
        Args:
            group_id: 群组 ID
            username: 被邀请用户名
            user_public_key: 被邀请用户的公钥
            
        Returns:
            是否成功
        """
        # 获取群组密钥
        group_key = self.key_manager.get_group_key(group_id)
        if not group_key:
            return False
        
        # 使用被邀请用户的公钥加密群组密钥
        encrypted_group_key = self.key_manager.encrypt_for_user(
            group_key, user_public_key
        )
        
        result = self.network.invite_to_group(
            group_id, username, encrypted_group_key.hex()
        )
        return result.get('success', False)
    
    def accept_invitation(self, invitation_id: int) -> bool:
        """
        接受邀请
        
        Args:
            invitation_id: 邀请 ID
            
        Returns:
            是否成功
        """
        # 找到邀请
        invitation = next(
            (inv for inv in self.invitations if inv.id == invitation_id),
            None
        )
        if not invitation:
            return False
        
        result = self.network.respond_invitation(invitation_id, accept=True)
        if result.get('success'):
            # 解密群组密钥
            try:
                group_key = self.key_manager.decrypt_for_me(
                    invitation.encrypted_group_key
                )
                self.key_manager.set_group_key(invitation.group_id, group_key)
            except Exception:
                pass
            
            self.refresh_groups()
            return True
        return False
    
    def reject_invitation(self, invitation_id: int) -> bool:
        """拒绝邀请"""
        result = self.network.respond_invitation(invitation_id, accept=False)
        if result.get('success'):
            self.refresh_groups()
            return True
        return False
    
    def leave_group(self, group_id: int) -> bool:
        """退出群组"""
        result = self.network.leave_group(group_id)
        if result.get('success'):
            # 清除群组密钥
            self.key_manager.group_keys.pop(group_id, None)
            self.refresh_groups()
            return True
        return False
    
    def get_group_by_id(self, group_id: int) -> Optional[Group]:
        """根据 ID 获取群组"""
        return next((g for g in self.groups if g.id == group_id), None)
