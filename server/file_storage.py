"""
文件存储管理模块
处理加密文件的物理存储
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime


class FileStorage:
    """文件存储管理器"""
    
    def __init__(self, base_path: Path):
        """
        初始化文件存储
        
        Args:
            base_path: 存储根目录
        """
        self.base_path = Path(base_path)
        self.users_path = self.base_path / "users"
        self.groups_path = self.base_path / "groups"
        
        # 确保目录存在
        self.users_path.mkdir(parents=True, exist_ok=True)
        self.groups_path.mkdir(parents=True, exist_ok=True)
    
    def get_user_storage_path(self, user_id: int) -> Path:
        """获取用户存储路径"""
        path = self.users_path / str(user_id)
        path.mkdir(exist_ok=True)
        return path
    
    def get_group_storage_path(self, group_id: int) -> Path:
        """获取群组存储路径"""
        path = self.groups_path / str(group_id)
        path.mkdir(exist_ok=True)
        return path
    
    def generate_storage_path(self, user_id: int = None, group_id: int = None) -> str:
        """
        生成唯一的存储路径
        
        Args:
            user_id: 用户 ID（个人空间）
            group_id: 群组 ID（群组空间）
            
        Returns:
            相对于 base_path 的存储路径
        """
        # 使用日期分层存储
        date_path = datetime.now().strftime("%Y/%m/%d")
        filename = f"{uuid.uuid4().hex}.enc"
        
        if user_id:
            return f"users/{user_id}/{date_path}/{filename}"
        elif group_id:
            return f"groups/{group_id}/{date_path}/{filename}"
        else:
            raise ValueError("必须指定 user_id 或 group_id")
    
    def get_absolute_path(self, storage_path: str) -> Path:
        """获取绝对路径"""
        return self.base_path / storage_path
    
    def save_file(self, storage_path: str, data: bytes) -> bool:
        """
        保存文件数据
        
        Args:
            storage_path: 相对存储路径
            data: 加密的文件数据
            
        Returns:
            是否成功
        """
        try:
            abs_path = self.get_absolute_path(storage_path)
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(abs_path, 'wb') as f:
                f.write(data)
            return True
        except Exception as e:
            print(f"[FileStorage] 保存文件失败: {e}")
            return False
    
    def save_file_stream(self, storage_path: str, stream: BinaryIO, 
                         chunk_size: int = 65536) -> int:
        """
        流式保存文件
        
        Args:
            storage_path: 相对存储路径
            stream: 文件流
            chunk_size: 块大小
            
        Returns:
            写入的总字节数
        """
        try:
            abs_path = self.get_absolute_path(storage_path)
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            
            total_size = 0
            with open(abs_path, 'wb') as f:
                while True:
                    chunk = stream.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    total_size += len(chunk)
            return total_size
        except Exception as e:
            print(f"[FileStorage] 流式保存失败: {e}")
            return -1
    
    def read_file(self, storage_path: str) -> Optional[bytes]:
        """
        读取文件数据
        
        Args:
            storage_path: 相对存储路径
            
        Returns:
            文件数据，失败返回 None
        """
        try:
            abs_path = self.get_absolute_path(storage_path)
            if not abs_path.exists():
                return None
            
            with open(abs_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"[FileStorage] 读取文件失败: {e}")
            return None
    
    def read_file_stream(self, storage_path: str, 
                         chunk_size: int = 65536):
        """
        流式读取文件（生成器）
        
        Args:
            storage_path: 相对存储路径
            chunk_size: 块大小
            
        Yields:
            文件数据块
        """
        abs_path = self.get_absolute_path(storage_path)
        if not abs_path.exists():
            return
        
        with open(abs_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    def delete_file(self, storage_path: str) -> bool:
        """
        删除文件
        
        Args:
            storage_path: 相对存储路径
            
        Returns:
            是否成功
        """
        try:
            abs_path = self.get_absolute_path(storage_path)
            if abs_path.exists():
                abs_path.unlink()
            return True
        except Exception as e:
            print(f"[FileStorage] 删除文件失败: {e}")
            return False
    
    def get_file_size(self, storage_path: str) -> int:
        """获取文件大小"""
        abs_path = self.get_absolute_path(storage_path)
        if abs_path.exists():
            return abs_path.stat().st_size
        return 0
    
    def file_exists(self, storage_path: str) -> bool:
        """检查文件是否存在"""
        return self.get_absolute_path(storage_path).exists()
    
    def get_user_storage_usage(self, user_id: int) -> int:
        """获取用户存储使用量（字节）"""
        user_path = self.get_user_storage_path(user_id)
        total = 0
        for file in user_path.rglob('*'):
            if file.is_file():
                total += file.stat().st_size
        return total
    
    def get_group_storage_usage(self, group_id: int) -> int:
        """获取群组存储使用量（字节）"""
        group_path = self.get_group_storage_path(group_id)
        total = 0
        for file in group_path.rglob('*'):
            if file.is_file():
                total += file.stat().st_size
        return total
    
    def cleanup_empty_dirs(self, storage_path: str):
        """清理空目录"""
        abs_path = self.get_absolute_path(storage_path).parent
        while abs_path != self.base_path:
            try:
                if abs_path.is_dir() and not any(abs_path.iterdir()):
                    abs_path.rmdir()
                    abs_path = abs_path.parent
                else:
                    break
            except Exception:
                break
