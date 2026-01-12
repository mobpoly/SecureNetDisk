"""
登录对话框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QWidget, QMessageBox, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from .styles import StyleSheet


class LoginDialog(QDialog):
    """登录对话框"""
    login_success = pyqtSignal(dict)
    
    def __init__(self, network_client, key_manager, parent=None):
        super().__init__(parent)
        self.network = network_client
        self.key_manager = key_manager
        self.setWindowTitle("安全网盘 - 登录")
        self.setFixedSize(440, 580)
        self.setStyleSheet(StyleSheet.LOGIN)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)
        
        logo = QLabel("🔐 安全网盘")
        logo.setObjectName("logoLabel")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        layout.addSpacing(20)
        
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_login_page())      # 0
        self.stack.addWidget(self._create_register_page())   # 1
        self.stack.addWidget(self._create_recovery_page())   # 2
        layout.addWidget(self.stack)
    
    def _create_login_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        
        layout.addWidget(QLabel("登录您的账号"))
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)
        
        login_btn = QPushButton("登录")
        login_btn.setObjectName("loginButton")
        login_btn.clicked.connect(self._do_login)
        layout.addWidget(login_btn)
        
        # 忘记密码按钮
        forgot_btn = QPushButton("忘记密码？使用恢复密钥")
        forgot_btn.setObjectName("linkButton")
        forgot_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        layout.addWidget(forgot_btn)
        
        layout.addStretch()
        
        reg_btn = QPushButton("没有账号？点击注册")
        reg_btn.setObjectName("linkButton")
        reg_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        layout.addWidget(reg_btn)
        
        return page
    
    def _create_register_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        
        back_btn = QPushButton("← 返回")
        back_btn.setObjectName("linkButton")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(QLabel("创建账号"))
        
        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("用户名")
        layout.addWidget(self.reg_username)
        
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("邮箱")
        layout.addWidget(self.reg_email)
        
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("密码")
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.reg_password)
        
        reg_btn = QPushButton("注册")
        reg_btn.setObjectName("loginButton")
        reg_btn.clicked.connect(self._do_register)
        layout.addWidget(reg_btn)
        
        layout.addStretch()
        return page
    
    def _create_recovery_page(self):
        """创建密码恢复页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        
        back_btn = QPushButton("← 返回登录")
        back_btn.setObjectName("linkButton")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(QLabel("🔑 使用恢复密钥重置密码"))
        
        self.recovery_username = QLineEdit()
        self.recovery_username.setPlaceholderText("用户名")
        layout.addWidget(self.recovery_username)
        
        self.recovery_key_input = QLineEdit()
        self.recovery_key_input.setPlaceholderText("恢复密钥")
        layout.addWidget(self.recovery_key_input)
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("新密码")
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.new_password_input)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("确认新密码")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_password_input)
        
        reset_btn = QPushButton("重置密码")
        reset_btn.setObjectName("loginButton")
        reset_btn.clicked.connect(self._do_recovery)
        layout.addWidget(reset_btn)
        
        layout.addStretch()
        return page
    
    def _do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return
        
        # 使用 SHA-256 预哈希密码后再发送（避免明文传输）
        from auth.password import PasswordManager
        password_prehash = PasswordManager.prehash_password(password)
        result = self.network.login_password(username, password_prehash)
        
        if result.get('success'):
            if self.key_manager.unlock_with_password(password, result):
                self.login_success.emit(result)
                self.accept()
            else:
                QMessageBox.critical(self, "错误", "密钥解锁失败")
        else:
            QMessageBox.critical(self, "错误", result.get('error', '登录失败'))
    
    def _do_register(self):
        username = self.reg_username.text().strip()
        email = self.reg_email.text().strip()
        password = self.reg_password.text()
        
        if not username or not email or not password:
            QMessageBox.warning(self, "提示", "请填写所有字段")
            return
        
        # 验证邮箱格式
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            QMessageBox.warning(self, "提示", "邮箱格式不正确")
            return
        
        # 验证密码强度
        from auth.password import PasswordManager
        valid, msg = PasswordManager.validate_password(password)
        if not valid:
            QMessageBox.warning(self, "提示", msg)
            return
        
        reg_data = self.key_manager.prepare_registration(password)
        result = self.network.register(
            username=username, email=email,
            password_hash=reg_data['password_hash'],
            public_key=reg_data['public_key'],
            encrypted_private_key=reg_data['encrypted_private_key'],
            encrypted_master_key=reg_data['encrypted_master_key'],
            master_key_salt=reg_data['master_key_salt'],
            recovery_key_encrypted=reg_data['recovery_key_encrypted'],
            recovery_key_salt=reg_data['recovery_key_salt'],
            recovery_key_hash=reg_data['recovery_key_hash']
        )
        
        if result.get('success'):
            QMessageBox.information(self, "成功", 
                f"注册成功！请保存恢复密钥:\n\n{reg_data['recovery_key']}")
            self.stack.setCurrentIndex(0)
        else:
            QMessageBox.critical(self, "错误", result.get('error', '注册失败'))
    
    def _do_recovery(self):
        """执行密码恢复"""
        username = self.recovery_username.text().strip()
        recovery_key = self.recovery_key_input.text().strip()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        if not username or not recovery_key or not new_password:
            QMessageBox.warning(self, "提示", "请填写所有字段")
            return
        
        if new_password != confirm_password:
            QMessageBox.warning(self, "提示", "两次输入的密码不一致")
            return
        
        # 验证密码强度
        from auth.password import PasswordManager
        valid, msg = PasswordManager.validate_password(new_password)
        if not valid:
            QMessageBox.warning(self, "提示", msg)
            return
        
        # 1. 先用恢复密钥获取用户数据
        result = self.network.get_user_for_recovery(username)
        if not result.get('success'):
            QMessageBox.critical(self, "错误", result.get('error', '获取用户信息失败'))
            return
        
        # 2. 使用恢复密钥解锁主密钥
        if not self.key_manager.unlock_with_recovery(recovery_key, result):
            QMessageBox.critical(self, "错误", "恢复密钥无效")
            return
        
        # 3. 准备新密码数据
        reset_data = self.key_manager.prepare_password_reset(new_password)
        
        # 4. 发送密码重置请求
        reset_result = self.network.reset_password(
            username=username,
            recovery_key=recovery_key,
            new_password_hash=reset_data['new_password_hash'],
            new_encrypted_master_key=reset_data['new_encrypted_master_key'],
            new_master_key_salt=reset_data['new_master_key_salt']
        )
        
        if reset_result.get('success'):
            QMessageBox.information(self, "成功", "密码重置成功，请使用新密码登录")
            self.key_manager.lock()
            self.stack.setCurrentIndex(0)
        else:
            QMessageBox.critical(self, "错误", reset_result.get('error', '密码重置失败'))
