"""
Email 服务模块
发送验证码和密码重置邮件
"""

import os
import random
import string
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from threading import Lock


@dataclass
class VerificationCode:
    """验证码信息"""
    code: str
    email: str
    created_at: float
    expires_at: float
    purpose: str  # "login" or "reset"


class EmailService:
    """Email 服务"""
    
    CODE_LENGTH = 6
    CODE_EXPIRY = 300  # 5 分钟
    MAX_ATTEMPTS = 5   # 最大尝试次数
    
    def __init__(self, 
                 smtp_host: str = None,
                 smtp_port: int = 587,
                 smtp_user: str = None,
                 smtp_password: str = None,
                 sender_email: str = None,
                 sender_name: str = "安全网盘"):
        """
        初始化 Email 服务
        
        Args:
            smtp_host: SMTP 服务器地址
            smtp_port: SMTP 端口
            smtp_user: SMTP 用户名
            smtp_password: SMTP 密码
            sender_email: 发件人地址
            sender_name: 发件人名称
        """
        self.smtp_host = smtp_host or os.environ.get('SMTP_HOST', '')
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user or os.environ.get('SMTP_USER', '')
        self.smtp_password = smtp_password or os.environ.get('SMTP_PASSWORD', '')
        self.sender_email = sender_email or self.smtp_user
        self.sender_name = sender_name
        
        # 验证码存储
        self._codes: Dict[str, VerificationCode] = {}
        self._attempts: Dict[str, int] = {}
        self._lock = Lock()
    
    @property
    def is_configured(self) -> bool:
        """检查是否已配置 SMTP"""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)
    
    def generate_code(self, email: str, purpose: str = "login") -> str:
        """
        生成验证码
        
        Args:
            email: 目标邮箱
            purpose: 用途 ("login" 或 "reset")
            
        Returns:
            生成的验证码
        """
        code = ''.join(random.choices(string.digits, k=self.CODE_LENGTH))
        
        with self._lock:
            key = f"{email}:{purpose}"
            self._codes[key] = VerificationCode(
                code=code,
                email=email,
                created_at=time.time(),
                expires_at=time.time() + self.CODE_EXPIRY,
                purpose=purpose
            )
            self._attempts[key] = 0
        
        return code
    
    def verify_code(self, email: str, code: str, purpose: str = "login") -> Tuple[bool, str]:
        """
        验证验证码
        
        Args:
            email: 邮箱地址
            code: 用户输入的验证码
            purpose: 用途
            
        Returns:
            (是否有效, 错误消息)
        """
        with self._lock:
            key = f"{email}:{purpose}"
            
            # 检查尝试次数
            attempts = self._attempts.get(key, 0)
            if attempts >= self.MAX_ATTEMPTS:
                self._codes.pop(key, None)
                return False, "验证码已失效，请重新获取"
            
            stored = self._codes.get(key)
            if not stored:
                return False, "验证码不存在或已过期"
            
            # 检查过期
            if time.time() > stored.expires_at:
                self._codes.pop(key, None)
                return False, "验证码已过期"
            
            # 验证
            if stored.code != code:
                self._attempts[key] = attempts + 1
                remaining = self.MAX_ATTEMPTS - attempts - 1
                return False, f"验证码错误，剩余 {remaining} 次尝试"
            
            # 验证成功，清除
            self._codes.pop(key, None)
            self._attempts.pop(key, None)
            return True, ""
    
    def send_verification_code(self, email: str, purpose: str = "login") -> Tuple[bool, str]:
        """
        发送验证码邮件
        
        Args:
            email: 目标邮箱
            purpose: 用途
            
        Returns:
            (是否成功, 错误消息或验证码)
        """
        code = self.generate_code(email, purpose)
        
        # 控制台输出（用于调试）
        print(f"[EmailService] 验证码 -> {email}: {code} (用途: {purpose})")
        
        if not self.is_configured:
            # 未配置 SMTP，仅返回验证码（开发模式）
            return True, code
        
        try:
            subject = "登录验证码" if purpose == "login" else "密码重置验证码"
            body = self._create_code_email_body(code, purpose)
            
            self._send_email(email, subject, body)
            return True, ""
        except Exception as e:
            print(f"[EmailService] 发送失败: {e}")
            return True, code  # 发送失败时也返回验证码（保证可用性）
    
    def send_recovery_email(self, email: str, recovery_token: str) -> bool:
        """
        发送密钥恢复邮件
        
        Args:
            email: 目标邮箱
            recovery_token: 恢复令牌
            
        Returns:
            是否成功
        """
        print(f"[EmailService] 恢复令牌 -> {email}: {recovery_token}")
        
        if not self.is_configured:
            return True
        
        try:
            subject = "密钥恢复凭证"
            body = self._create_recovery_email_body(recovery_token)
            self._send_email(email, subject, body)
            return True
        except Exception as e:
            print(f"[EmailService] 发送失败: {e}")
            return True
    
    def _send_email(self, to_email: str, subject: str, body: str):
        """发送邮件"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = formataddr((str(Header(self.sender_name, 'utf-8')), self.sender_email))
        msg['To'] = to_email
        
        # HTML 内容
        html_part = MIMEText(body, 'html', 'utf-8')
        msg.attach(html_part)
        
        # 根据端口选择连接方式
        # SSL端口: 465(QQ/网易), 994(网易)
        # TLS端口: 587
        if self.smtp_port in (465, 994):
            # SSL 模式 (端口 465, 994)
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
            try:
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            finally:
                server.quit()
        else:
            # TLS 模式 (端口 587)
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            try:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            finally:
                server.quit()
    
    def _create_code_email_body(self, code: str, purpose: str) -> str:
        """创建验证码邮件内容"""
        title = "登录验证" if purpose == "login" else "密码重置"
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f5f5; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #1a73e8; margin-bottom: 20px;">{title}</h2>
                <p style="color: #666; font-size: 14px;">您的验证码是：</p>
                <div style="background: #f0f7ff; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                    <span style="font-size: 32px; font-weight: bold; color: #1a73e8; letter-spacing: 8px;">{code}</span>
                </div>
                <p style="color: #999; font-size: 12px;">验证码有效期 5 分钟，请勿泄露给他人。</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">此邮件由安全网盘系统自动发送，请勿回复。</p>
            </div>
        </body>
        </html>
        """
    
    def _create_recovery_email_body(self, token: str) -> str:
        """创建恢复邮件内容"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f5f5; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #1a73e8; margin-bottom: 20px;">密钥恢复</h2>
                <p style="color: #666; font-size: 14px;">您的恢复凭证：</p>
                <div style="background: #fff3e0; border-radius: 8px; padding: 15px; margin: 20px 0; word-break: break-all;">
                    <code style="font-size: 14px; color: #e65100;">{token}</code>
                </div>
                <p style="color: #f44336; font-size: 12px;">⚠️ 请妥善保管此凭证，它是恢复您加密文件的唯一方式。</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">此邮件由安全网盘系统自动发送，请勿回复。</p>
            </div>
        </body>
        </html>
        """
