"""
安全数据包格式定义
自定义协议的数据包结构
"""

import struct
import time
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional


class PacketType(IntEnum):
    """数据包类型"""
    # 握手相关
    CLIENT_HELLO = 0x01
    SERVER_HELLO = 0x02
    KEY_EXCHANGE = 0x03
    FINISHED = 0x04
    
    # 认证相关
    AUTH_REQUEST = 0x10
    AUTH_RESPONSE = 0x11
    REGISTER_REQUEST = 0x12
    REGISTER_RESPONSE = 0x13
    EMAIL_CODE_REQUEST = 0x14
    EMAIL_CODE_RESPONSE = 0x15
    PASSWORD_RESET_REQUEST = 0x16
    PASSWORD_RESET_RESPONSE = 0x17
    
    # 文件操作
    FILE_LIST_REQUEST = 0x20
    FILE_LIST_RESPONSE = 0x21
    FILE_UPLOAD_START = 0x22
    FILE_UPLOAD_DATA = 0x23
    FILE_UPLOAD_END = 0x24
    FILE_DOWNLOAD_REQUEST = 0x25
    FILE_DOWNLOAD_START = 0x26
    FILE_DOWNLOAD_DATA = 0x27
    FILE_DOWNLOAD_END = 0x28
    FILE_DELETE_REQUEST = 0x29
    FILE_DELETE_RESPONSE = 0x2A
    FILE_RENAME_REQUEST = 0x2B
    FILE_RENAME_RESPONSE = 0x2C
    FOLDER_CREATE_REQUEST = 0x2D
    FOLDER_CREATE_RESPONSE = 0x2E
    FILE_UPLOAD_CANCEL = 0x2F
    
    # 群组操作
    GROUP_CREATE_REQUEST = 0x30
    GROUP_CREATE_RESPONSE = 0x31
    GROUP_LIST_REQUEST = 0x32
    GROUP_LIST_RESPONSE = 0x33
    GROUP_INVITE_REQUEST = 0x34
    GROUP_INVITE_RESPONSE = 0x35
    GROUP_JOIN_REQUEST = 0x36
    GROUP_JOIN_RESPONSE = 0x37
    GROUP_LEAVE_REQUEST = 0x38
    GROUP_LEAVE_RESPONSE = 0x39
    GROUP_KEY_REQUEST = 0x3A
    GROUP_KEY_RESPONSE = 0x3B
    GROUP_MEMBERS_REQUEST = 0x3C
    GROUP_MEMBERS_RESPONSE = 0x3D
    
    # 用户信息
    USER_PUBLIC_KEY_REQUEST = 0x40
    USER_PUBLIC_KEY_RESPONSE = 0x41
    
    # 通知
    NOTIFICATION_COUNT_REQUEST = 0x50
    NOTIFICATION_COUNT_RESPONSE = 0x51
    NOTIFICATION_READ_REQUEST = 0x52
    NOTIFICATION_READ_RESPONSE = 0x53
    
    # 通用
    ERROR = 0xFE
    HEARTBEAT = 0xFF


class PacketFlags(IntEnum):
    """数据包标志"""
    NONE = 0x0000
    ENCRYPTED = 0x0001      # 数据已加密
    COMPRESSED = 0x0002     # 数据已压缩
    FRAGMENTED = 0x0004     # 分片数据包
    LAST_FRAGMENT = 0x0008  # 最后一个分片
    REQUIRES_ACK = 0x0010   # 需要确认


# 数据包格式:
# +----------------+----------------+----------------+----------------+
# |  Magic (4B)    |  Version (1B)  |  Type (1B)     |  Flags (2B)    |
# +----------------+----------------+----------------+----------------+
# |  Sequence Number (4B)          |  Timestamp (8B)                  |
# +----------------+----------------+----------------+----------------+
# |  Payload Length (4B)           |  HMAC (32B)                      |
# +----------------+----------------+----------------+----------------+
# |  Encrypted Payload (Variable)                                     |
# +----------------+----------------+----------------+----------------+

PACKET_MAGIC = b'\x53\x44\x49\x53'  # "SDIS" - Secure Disk System
PACKET_VERSION = 1
HEADER_SIZE = 4 + 1 + 1 + 2 + 4 + 8 + 4 + 32  # 56 bytes


@dataclass
class Packet:
    """安全数据包"""
    
    packet_type: PacketType
    payload: bytes
    flags: int = PacketFlags.NONE
    sequence: int = 0
    timestamp: int = 0
    hmac: bytes = b'\x00' * 32
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = int(time.time() * 1000)  # 毫秒时间戳
    
    def to_bytes(self) -> bytes:
        """
        序列化数据包（不含 HMAC 计算）
        
        Returns:
            序列化的字节数据
        """
        header = struct.pack(
            '>4sBBHIQI',
            PACKET_MAGIC,
            PACKET_VERSION,
            self.packet_type,
            self.flags,
            self.sequence,
            self.timestamp,
            len(self.payload)
        )
        return header + self.hmac + self.payload
    
    def get_hmac_data(self) -> bytes:
        """
        获取用于计算 HMAC 的数据
        
        Returns:
            需要认证的数据（头部 + 载荷，不含 HMAC 字段）
        """
        header = struct.pack(
            '>4sBBHIQI',
            PACKET_MAGIC,
            PACKET_VERSION,
            self.packet_type,
            self.flags,
            self.sequence,
            self.timestamp,
            len(self.payload)
        )
        return header + self.payload
    
    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['Packet']:
        """
        从字节数据反序列化
        
        Args:
            data: 完整的数据包字节
            
        Returns:
            反序列化的 Packet 对象，解析失败返回 None
        """
        if len(data) < HEADER_SIZE:
            return None
        
        try:
            magic, version, pkt_type, flags, seq, ts, payload_len = struct.unpack(
                '>4sBBHIQI', data[:24]
            )
            
            if magic != PACKET_MAGIC:
                return None
            if version != PACKET_VERSION:
                return None
            
            hmac_data = data[24:56]
            payload = data[56:56 + payload_len]
            
            if len(payload) != payload_len:
                return None
            
            return cls(
                packet_type=PacketType(pkt_type),
                payload=payload,
                flags=flags,
                sequence=seq,
                timestamp=ts,
                hmac=hmac_data
            )
        except Exception:
            return None
    
    @property
    def is_encrypted(self) -> bool:
        """是否已加密"""
        return bool(self.flags & PacketFlags.ENCRYPTED)
    
    @property
    def total_size(self) -> int:
        """数据包总大小"""
        return HEADER_SIZE + len(self.payload)


class PacketBuilder:
    """数据包构建器"""
    
    def __init__(self):
        self._sequence = 0
    
    def next_sequence(self) -> int:
        """获取下一个序列号"""
        self._sequence += 1
        return self._sequence
    
    def build(self, packet_type: PacketType, payload: bytes, 
              encrypted: bool = True) -> Packet:
        """
        构建数据包
        
        Args:
            packet_type: 数据包类型
            payload: 载荷数据
            encrypted: 是否标记为加密
            
        Returns:
            构建的 Packet 对象
        """
        flags = PacketFlags.ENCRYPTED if encrypted else PacketFlags.NONE
        return Packet(
            packet_type=packet_type,
            payload=payload,
            flags=flags,
            sequence=self.next_sequence()
        )
