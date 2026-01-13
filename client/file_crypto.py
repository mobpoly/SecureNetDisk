"""
文件加密模块
处理文件的客户端加解密
"""

import os
from typing import Tuple, Optional
from pathlib import Path

from crypto.aes import AESCipher


import tempfile

class FileCrypto:
    """文件加密器"""
    
    CHUNK_SIZE = 64 * 1024  # 64KB
    LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100MB
    
    @staticmethod
    def generate_file_key() -> bytes:
        """生成文件密钥"""
        return AESCipher.generate_key()
    
    @staticmethod
    def encrypt_file(file_path: Path, file_key: bytes) -> Tuple[bytes, int]:
        """
        加密文件 (分块处理，支持大文件)
        
        Args:
            file_path: 文件路径
            file_key: 文件密钥
            
        Returns:
            (加密数据, 原始大小) 元组
            对于大文件返回 (临时文件路径字符串, 原始大小)
        """
        file_size = file_path.stat().st_size
        
        # 对于小文件 (< 100MB)，使用内存加密 (CBC模式)
        if file_size < FileCrypto.LARGE_FILE_THRESHOLD:
            with open(file_path, 'rb') as f:
                plaintext = f.read()
            
            cipher = AESCipher(file_key)
            ciphertext, iv = cipher.encrypt_cbc(plaintext)
            # 格式: version(1) + iv(16) + ciphertext
            encrypted_data = b'\x00' + iv + ciphertext
            del plaintext
            return encrypted_data, file_size
        
        # 对于大文件 (>= 100MB)，流式加密到临时文件
        # 返回临时文件路径而不是数据，避免内存溢出
        import tempfile
        import gc
        from Crypto.Cipher import AES
        
        nonce = os.urandom(8)
        # 创建单个 CTR 密码对象，保持计数器状态
        ctr_cipher = AES.new(file_key, AES.MODE_CTR, nonce=nonce)
        
        # 创建临时文件
        temp_fd, temp_path = tempfile.mkstemp(suffix='.enc')
        
        with os.fdopen(temp_fd, 'wb') as temp_file:
            # 写入版本标记和 nonce
            temp_file.write(b'\x01')  # version 1 = CTR mode
            temp_file.write(nonce)
            
            # 分块读取并加密
            chunk_size = 1024 * 1024  # 1MB chunks
            
            with open(file_path, 'rb') as f:
                counter = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # 使用同一个 cipher 对象加密，保持计数器连续
                    encrypted_chunk = ctr_cipher.encrypt(chunk)
                    temp_file.write(encrypted_chunk)
                    
                    counter += 1
                    if counter % 100 == 0:
                        gc.collect()
        
        # 返回临时文件路径 (字符串类型表示是文件路径)
        return temp_path, file_size
    
    @staticmethod
    def decrypt_file(encrypted_data: bytes, file_key: bytes) -> bytes:
        """
        解密文件 (自动检测加密模式)
        
        Args:
            encrypted_data: 加密数据
            file_key: 文件密钥
            
        Returns:
            解密后的文件数据
        """
        cipher = AESCipher(file_key)
        
        # 检查版本标记
        version = encrypted_data[0]
        
        if version == 0:
            # CBC 模式: version(1) + iv(16) + ciphertext
            iv = encrypted_data[1:17]
            ciphertext = encrypted_data[17:]
            return cipher.decrypt_cbc(ciphertext, iv)
        elif version == 1:
            # CTR 模式: version(1) + nonce(8) + ciphertext
            nonce = encrypted_data[1:9]
            ciphertext = encrypted_data[9:]
            return cipher.decrypt_ctr(ciphertext, nonce)
        else:
            # 兼容旧格式 (无版本标记，直接是 iv + ciphertext)
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            return cipher.decrypt_cbc(ciphertext, iv)
    
    @staticmethod
    def decrypt_file_to_path(encrypted_data: bytes, file_key: bytes, output_path: Path):
        """
        解密文件并直接写入文件 (流式处理减少内存占用)
        
        Args:
            encrypted_data: 加密数据
            file_key: 文件密钥
            output_path: 输出文件路径
        """
        import gc
        from Crypto.Cipher import AES
        
        version = encrypted_data[0]
        
        if version == 0:
            # CBC 模式 - 小文件，一次性解密
            cipher = AESCipher(file_key)
            iv = encrypted_data[1:17]
            ciphertext = encrypted_data[17:]
            decrypted = cipher.decrypt_cbc(ciphertext, iv)
            with open(output_path, 'wb') as f:
                f.write(decrypted)
            del decrypted
            gc.collect()
            
        elif version == 1:
            # CTR 模式 - 大文件，流式解密
            nonce = encrypted_data[1:9]
            ciphertext = encrypted_data[9:]
            
            # 创建单个 CTR 密码对象
            ctr_cipher = AES.new(file_key, AES.MODE_CTR, nonce=nonce)
            
            # 流式解密写入文件
            chunk_size = 1024 * 1024  # 1MB chunks
            with open(output_path, 'wb') as f:
                offset = 0
                while offset < len(ciphertext):
                    chunk = ciphertext[offset:offset + chunk_size]
                    decrypted_chunk = ctr_cipher.decrypt(chunk)
                    f.write(decrypted_chunk)
                    offset += chunk_size
                    
                    if offset % (50 * chunk_size) == 0:
                        gc.collect()
            
            del ciphertext
            gc.collect()
            
        else:
            # 兼容旧格式
            cipher = AESCipher(file_key)
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            decrypted = cipher.decrypt_cbc(ciphertext, iv)
            with open(output_path, 'wb') as f:
                f.write(decrypted)
            del decrypted
            gc.collect()
    
    @staticmethod
    def decrypt_from_encrypted_file(encrypted_file_path: Path, file_key: bytes, output_path: Path):
        """
        从加密文件直接流式解密到输出文件 (避免加载整个文件到内存)
        
        Args:
            encrypted_file_path: 加密文件路径
            file_key: 文件密钥
            output_path: 输出文件路径
        """
        import gc
        from Crypto.Cipher import AES
        
        with open(encrypted_file_path, 'rb') as enc_file:
            # 读取版本标记
            version = enc_file.read(1)[0]
            
            if version == 0:
                # CBC 模式 - 小文件
                iv = enc_file.read(16)
                ciphertext = enc_file.read()
                cipher = AESCipher(file_key)
                decrypted = cipher.decrypt_cbc(ciphertext, iv)
                with open(output_path, 'wb') as f:
                    f.write(decrypted)
                del decrypted
                gc.collect()
                
            elif version == 1:
                # CTR 模式 - 大文件，流式解密
                nonce = enc_file.read(8)
                ctr_cipher = AES.new(file_key, AES.MODE_CTR, nonce=nonce)
                
                chunk_size = 1024 * 1024  # 1MB chunks
                with open(output_path, 'wb') as out_file:
                    counter = 0
                    while True:
                        chunk = enc_file.read(chunk_size)
                        if not chunk:
                            break
                        
                        decrypted_chunk = ctr_cipher.decrypt(chunk)
                        out_file.write(decrypted_chunk)
                        
                        counter += 1
                        if counter % 100 == 0:
                            gc.collect()
                
            else:
                # 兼容旧格式 - 整个读取
                enc_file.seek(0)
                encrypted_data = enc_file.read()
                cipher = AESCipher(file_key)
                iv = encrypted_data[:16]
                ciphertext = encrypted_data[16:]
                decrypted = cipher.decrypt_cbc(ciphertext, iv)
                with open(output_path, 'wb') as f:
                    f.write(decrypted)
                del decrypted
                del encrypted_data
                gc.collect()
    
    @staticmethod
    def encrypt_file_streaming(file_path: Path, file_key: bytes):
        """
        流式加密文件（生成器）
        
        Args:
            file_path: 文件路径
            file_key: 文件密钥
            
        Yields:
            加密数据块
        """
        # 使用 CTR 模式支持流式加密
        cipher = AESCipher(file_key)
        nonce = os.urandom(8)
        
        # 首先 yield nonce
        yield nonce
        
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(FileCrypto.CHUNK_SIZE)
                if not chunk:
                    break
                
                encrypted_chunk, _ = cipher.encrypt_ctr(chunk, nonce)
                yield encrypted_chunk
    
    @staticmethod
    def encrypt_data(data: bytes, file_key: bytes) -> bytes:
        """
        加密内存中的数据
        
        Args:
            data: 明文数据
            file_key: 密钥
            
        Returns:
            加密数据（IV + 密文）
        """
        cipher = AESCipher(file_key)
        ciphertext, iv = cipher.encrypt_cbc(data)
        return iv + ciphertext
    
    @staticmethod
    def decrypt_data(encrypted_data: bytes, file_key: bytes) -> bytes:
        """
        解密内存中的数据
        
        Args:
            encrypted_data: 加密数据（IV + 密文）
            file_key: 密钥
            
        Returns:
            解密后的数据
        """
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        cipher = AESCipher(file_key)
        return cipher.decrypt_cbc(ciphertext, iv)


class FileKeyManager:
    """文件密钥管理器"""
    
    def __init__(self, master_key: bytes):
        """
        初始化文件密钥管理器
        
        Args:
            master_key: 用户主密钥
        """
        self.master_key = master_key
    
    def encrypt_file_key(self, file_key: bytes) -> bytes:
        """
        使用主密钥加密文件密钥
        
        Args:
            file_key: 文件密钥
            
        Returns:
            加密后的文件密钥
        """
        cipher = AESCipher(self.master_key)
        encrypted, iv = cipher.encrypt_cbc(file_key)
        return iv + encrypted
    
    def decrypt_file_key(self, encrypted_file_key: bytes) -> bytes:
        """
        解密文件密钥
        
        Args:
            encrypted_file_key: 加密的文件密钥
            
        Returns:
            文件密钥
        """
        iv = encrypted_file_key[:16]
        ciphertext = encrypted_file_key[16:]
        
        cipher = AESCipher(self.master_key)
        return cipher.decrypt_cbc(ciphertext, iv)
    
    def prepare_upload(self, file_path: Path) -> Tuple[bytes, bytes, bytes]:
        """
        准备文件上传
        
        Args:
            file_path: 文件路径
            
        Returns:
            (加密数据, 加密的文件密钥, 文件密钥) 元组
        """
        # 生成文件密钥
        file_key = FileCrypto.generate_file_key()
        
        # 加密文件
        encrypted_data, _ = FileCrypto.encrypt_file(file_path, file_key)
        
        # 加密文件密钥
        encrypted_file_key = self.encrypt_file_key(file_key)
        
        return encrypted_data, encrypted_file_key, file_key
    
    def decrypt_download(self, encrypted_data: bytes, 
                         encrypted_file_key: bytes) -> bytes:
        """
        解密下载的文件
        
        Args:
            encrypted_data: 加密的文件数据
            encrypted_file_key: 加密的文件密钥
            
        Returns:
            解密后的文件数据
        """
        # 解密文件密钥
        file_key = self.decrypt_file_key(encrypted_file_key)
        
        # 解密文件
        return FileCrypto.decrypt_file(encrypted_data, file_key)
