"""
主窗口
Google Drive 风格界面
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QHeaderView, QMenu, QFileDialog,
    QMessageBox, QInputDialog, QProgressDialog, QSplitter,
    QFrame, QToolBar, QStatusBar
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QIcon
from pathlib import Path

from .styles import StyleSheet, Icons


class FileItem:
    """文件项数据"""
    def __init__(self, data: dict):
        self.id = data.get('id')
        self.name = data.get('name', '')
        self.is_folder = data.get('is_folder', False)
        self.size = data.get('size', 0)
        self.created_at = data.get('created_at', '')
        self.encrypted_file_key = data.get('encrypted_file_key', '')
        self.uploader_name = data.get('uploader_name', '')


class MainWindow(QMainWindow):
    """主窗口"""
    
    logout_requested = pyqtSignal()  # 退出登录信号
    
    def __init__(self, network, key_manager, device_trust=None):
        super().__init__()
        self.network = network
        self.key_manager = key_manager
        self.device_trust = device_trust
        self.current_path = []  # 当前路径栈
        self.current_group_id = None
        self.files = []
        
        self.setWindowTitle("安全网盘")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(StyleSheet.MAIN)
        
        self._init_ui()
        self._refresh_files()
    
    def _init_ui(self):
        """初始化界面"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 侧边栏
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)
        
        # 主内容区
        content = self._create_content()
        main_layout.addWidget(content, 1)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def _create_sidebar(self) -> QWidget:
        """创建侧边栏"""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(4)
        
        # 新建按钮
        new_btn = QPushButton("➕ 功能")
        new_btn.setObjectName("fabButton")
        new_btn.clicked.connect(self._show_new_menu)
        layout.addWidget(new_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(16)
        
        # 导航按钮
        self.nav_my_drive = QPushButton(f"{Icons.HOME} 我的云盘")
        self.nav_my_drive.setCheckable(True)
        self.nav_my_drive.setChecked(True)
        self.nav_my_drive.clicked.connect(self._nav_my_drive)
        layout.addWidget(self.nav_my_drive)
        
        self.nav_groups = QPushButton(f"{Icons.GROUP} 共享群组")
        self.nav_groups.setCheckable(True)
        self.nav_groups.clicked.connect(self._nav_groups)
        layout.addWidget(self.nav_groups)
        
        layout.addStretch()
        
        # 用户信息和退出按钮
        if self.key_manager.user_keys:
            user_label = QLabel(f"👤 {self.key_manager.user_keys.username}")
            user_label.setStyleSheet("padding: 12px 24px; color: #5f6368;")
            layout.addWidget(user_label)
        
        # 退出登录按钮
        logout_btn = QPushButton("🚪 退出登录")
        logout_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #d93025;
                border: none;
                padding: 12px 24px;
                text-align: left;
            }
            QPushButton:hover {
                background: #fce8e6;
            }
        """)
        logout_btn.clicked.connect(self._do_logout)
        layout.addWidget(logout_btn)
        
        # 修改密码按钮
        change_pwd_btn = QPushButton("🔑 修改密码")
        change_pwd_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #1a73e8;
                border: none;
                padding: 12px 24px;
                text-align: left;
            }
            QPushButton:hover {
                background: #e8f0fe;
            }
        """)
        change_pwd_btn.clicked.connect(self._change_password)
        layout.addWidget(change_pwd_btn)
        
        # 解除设备信任按钮
        self.revoke_trust_btn = QPushButton("🔓 解除设备信任")
        self.revoke_trust_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #f57c00;
                border: none;
                padding: 12px 24px;
                text-align: left;
            }
            QPushButton:hover {
                background: #fff3e0;
            }
        """)
        self.revoke_trust_btn.clicked.connect(self._revoke_device_trust)
        layout.addWidget(self.revoke_trust_btn)
        
        return sidebar
    
    def _create_content(self) -> QWidget:
        """创建内容区"""
        content = QFrame()
        content.setObjectName("content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 16, 24, 16)
        
        # 工具栏
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # 面包屑导航
        breadcrumb_container = QWidget()
        self.breadcrumb_layout = QHBoxLayout(breadcrumb_container)
        self.breadcrumb_layout.setContentsMargins(0, 8, 0, 8)
        self.breadcrumb_layout.setSpacing(4)
        layout.addWidget(breadcrumb_container)

        # 文件列表
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(3)
        self.file_table.setHorizontalHeaderLabels(["名称", "大小", "修改时间"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(1, 100)
        self.file_table.setColumnWidth(2, 160)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self._show_context_menu)
        self.file_table.doubleClicked.connect(self._on_item_double_click)
        layout.addWidget(self.file_table)
        
        return content
    
    def _create_toolbar(self) -> QWidget:
        """创建工具栏"""
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        
        upload_btn = QPushButton(f"{Icons.UPLOAD} 上传文件")
        upload_btn.clicked.connect(self._upload_file)
        layout.addWidget(upload_btn)
        
        folder_btn = QPushButton(f"{Icons.NEW_FOLDER} 新建文件夹")
        folder_btn.clicked.connect(self._create_folder)
        layout.addWidget(folder_btn)
        
        layout.addStretch()
        
        refresh_btn = QPushButton(f"{Icons.SYNC} 刷新")
        refresh_btn.clicked.connect(self._refresh_files)
        layout.addWidget(refresh_btn)
        
        return toolbar
    
    def _show_new_menu(self):
        """显示新建菜单"""
        menu = QMenu(self)
        menu.addAction("📁 新建文件夹", self._create_folder)
        menu.addAction("⬆️ 上传文件", self._upload_file)
        menu.addSeparator()
        menu.addAction("👥 创建群组", self._create_group)
        menu.addAction("📨 邀请用户加入群组", self._invite_to_group)
        menu.addAction("📬 查看待处理邀请", self._view_invitations)
        menu.exec(self.sender().mapToGlobal(self.sender().rect().bottomLeft()))
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        item = self.file_table.itemAt(pos)
        if not item:
            return
        
        row = item.row()
        if row >= len(self.files):
            return
        
        file = self.files[row]
        menu = QMenu(self)
        
        if not file.is_folder:
            menu.addAction(f"{Icons.DOWNLOAD} 下载", lambda: self._download_file(file))
        
        menu.addAction(f"{Icons.RENAME} 重命名", lambda: self._rename_file(file))
        menu.addAction(f"{Icons.DELETE} 删除", lambda: self._delete_file(file))
        
        menu.exec(self.file_table.viewport().mapToGlobal(pos))

    def _refresh_files(self):
        """刷新文件列表"""
        parent_id = self.current_path[-1][0] if self.current_path else None
        result = self.network.get_file_list(parent_id=parent_id, group_id=self.current_group_id)

        if result.get('success'):
            self.files = [FileItem(f) for f in result.get('files', [])]
            self._update_file_table()
            self._create_breadcrumb()  # 刷新后更新面包屑
        else:
            self.statusBar().showMessage(f"刷新失败: {result.get('error', '未知错误')}")

    def _update_file_table(self):
        """更新文件表格"""
        # 根据是否在群组中设置列数
        if self.current_group_id:
            self.file_table.setColumnCount(4)
            self.file_table.setHorizontalHeaderLabels(["名称", "上传者", "大小", "上传时间"])
            self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            self.file_table.setColumnWidth(1, 120)
            self.file_table.setColumnWidth(2, 100)
            self.file_table.setColumnWidth(3, 160)
        else:
            self.file_table.setColumnCount(3)
            self.file_table.setHorizontalHeaderLabels(["名称", "大小", "上传时间"])
            self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self.file_table.setColumnWidth(1, 100)
            self.file_table.setColumnWidth(2, 160)
        
        self.file_table.setRowCount(len(self.files))
        
        for i, file in enumerate(self.files):
            icon = Icons.FOLDER if file.is_folder else Icons.get_file_icon(file.name)
            name_item = QTableWidgetItem(f"{icon}  {file.name}")
            size_item = QTableWidgetItem(self._format_size(file.size) if not file.is_folder else "-")
            time_item = QTableWidgetItem(file.created_at[:16] if file.created_at else "-")
            
            if self.current_group_id:
                uploader_item = QTableWidgetItem(f"👤 {file.uploader_name}" if file.uploader_name else "-")
                uploader_item.setForeground(Qt.GlobalColor.darkGray)
                self.file_table.setItem(i, 0, name_item)
                self.file_table.setItem(i, 1, uploader_item)
                self.file_table.setItem(i, 2, size_item)
                self.file_table.setItem(i, 3, time_item)
            else:
                self.file_table.setItem(i, 0, name_item)
                self.file_table.setItem(i, 1, size_item)
                self.file_table.setItem(i, 2, time_item)
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _on_item_double_click(self, index):
        """双击进入文件夹"""
        row = index.row()
        if row < len(self.files):
            file = self.files[row]
            if file.is_folder:
                # 将文件夹添加到路径中
                self.current_path.append((file.id, file.name))
                self._create_breadcrumb()
                self._refresh_files()
    
    def _nav_my_drive(self):
        """导航到我的云盘"""
        self.nav_my_drive.setChecked(True)
        self.nav_groups.setChecked(False)
        self.current_group_id = None
        self.current_path = []
        self._create_breadcrumb()
        self._refresh_files()
    
    def _nav_groups(self):
        """导航到群组"""
        self.nav_my_drive.setChecked(False)
        self.nav_groups.setChecked(True)
        # 显示群组选择
        self._show_group_selector()
    
    def _show_group_selector(self):
        """显示群组选择器"""
        result = self.network.get_groups()
        if not result.get('success'):
            QMessageBox.warning(self, "错误", result.get('error', '获取群组失败'))
            return

        groups = result.get('groups', [])
        if not groups:
            QMessageBox.information(self, "提示", "您还没有加入任何群组")
            return

        names = [g['name'] for g in groups]
        name, ok = QInputDialog.getItem(self, "选择群组", "请选择群组:", names, 0, False)

        if ok and name:
            idx = names.index(name)
            self.current_group_id = groups[idx]['id']
            self.current_path = []
            self._create_breadcrumb()
            self._refresh_files()

    def _upload_file(self):
        """上传文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if not file_path:
            return

        path = Path(file_path)
        self.statusBar().showMessage(f"正在上传 {path.name}...")

        try:
            from client.file_crypto import FileCrypto

            # 加密文件
            file_key = FileCrypto.generate_file_key()
            encrypted_data, _ = FileCrypto.encrypt_file(path, file_key)
            encrypted_file_key = self.key_manager.encrypt_file_key(file_key)

            # 正确提取 parent_id
            parent_id = self.current_path[-1][0] if self.current_path else None

            # 开始上传
            result = self.network.upload_file_start(
                filename=path.name,
                size=len(encrypted_data),
                encrypted_file_key=encrypted_file_key.hex(),
                parent_id=parent_id,
                group_id=self.current_group_id
            )

            if not result.get('success'):
                QMessageBox.critical(self, "错误", result.get('error', '上传失败'))
                return

            upload_id = result['upload_id']

            # 上传数据
            chunk_size = 64 * 1024
            for i in range(0, len(encrypted_data), chunk_size):
                chunk = encrypted_data[i:i + chunk_size]
                self.network.upload_file_data(upload_id, chunk)

            # 结束上传
            result = self.network.upload_file_end(upload_id)

            if result.get('success'):
                self.statusBar().showMessage("上传成功")
                self._refresh_files()
            else:
                QMessageBox.critical(self, "错误", result.get('error', '上传失败'))

        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _download_file(self, file: FileItem):
        """下载文件"""
        save_path, _ = QFileDialog.getSaveFileName(self, "保存文件", file.name)
        if not save_path:
            return
        
        self.statusBar().showMessage(f"正在下载 {file.name}...")
        
        try:
            result = self.network.download_file(file.id)
            
            if not result.get('success'):
                QMessageBox.critical(self, "错误", result.get('error', '下载失败'))
                return
            
            encrypted_data = bytes.fromhex(result['data'])
            encrypted_file_key = bytes.fromhex(result['encrypted_file_key'])
            
            # 解密
            from client.file_crypto import FileCrypto
            file_key = self.key_manager.decrypt_file_key(encrypted_file_key)
            decrypted_data = FileCrypto.decrypt_file(encrypted_data, file_key)
            
            with open(save_path, 'wb') as f:
                f.write(decrypted_data)
            
            self.statusBar().showMessage("下载成功")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _create_folder(self):
        """创建文件夹"""
        name, ok = QInputDialog.getText(self, "新建文件夹", "文件夹名称:")
        if ok and name:
            # 正确提取 parent_id
            parent_id = self.current_path[-1][0] if self.current_path else None
            result = self.network.create_folder(
                name=name,
                parent_id=parent_id,
                group_id=self.current_group_id
            )
            if result.get('success'):
                self._refresh_files()
            else:
                QMessageBox.critical(self, "错误", result.get('error', '创建失败'))

    def _rename_file(self, file: FileItem):
        """重命名文件"""
        name, ok = QInputDialog.getText(self, "重命名", "新名称:", text=file.name)
        if ok and name:
            result = self.network.rename_file(file.id, name)
            if result.get('success'):
                self._refresh_files()
            else:
                QMessageBox.critical(self, "错误", result.get('error', '重命名失败'))
    
    def _delete_file(self, file: FileItem):
        """删除文件"""
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除 {file.name} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            result = self.network.delete_file(file.id)
            if result.get('success'):
                self._refresh_files()
            else:
                QMessageBox.critical(self, "错误", result.get('error', '删除失败'))
    
    def _create_group(self):
        """创建群组"""
        name, ok = QInputDialog.getText(self, "创建群组", "群组名称:")
        if ok and name:
            result = self.network.create_group(name)
            if result.get('success'):
                QMessageBox.information(self, "成功", f"群组 {name} 创建成功")
            else:
                QMessageBox.critical(self, "错误", result.get('error', '创建失败'))
    
    def _invite_to_group(self):
        """邀请用户加入群组"""
        # 先选择群组
        result = self.network.get_groups()
        if not result.get('success'):
            QMessageBox.warning(self, "错误", result.get('error', '获取群组失败'))
            return
        
        groups = result.get('groups', [])
        if not groups:
            QMessageBox.information(self, "提示", "您还没有创建或加入任何群组")
            return
        
        names = [g['name'] for g in groups]
        group_name, ok = QInputDialog.getItem(self, "选择群组", "选择要邀请加入的群组:", names, 0, False)
        
        if not ok or not group_name:
            return
        
        idx = names.index(group_name)
        group = groups[idx]
        group_id = group['id']
        
        # 输入要邀请的用户名
        username, ok = QInputDialog.getText(self, "邀请用户", "请输入要邀请的用户名:")
        if not ok or not username:
            return
        
        try:
            # 获取被邀请用户的公钥
            key_result = self.network.get_user_public_key(username)
            if not key_result.get('success'):
                QMessageBox.critical(self, "错误", key_result.get('error', '获取用户信息失败'))
                return
            
            invitee_public_key = bytes.fromhex(key_result['public_key'])
            
            from groups.group_key import GroupKeyManager
            
            # 生成群组密钥（如果是新群组）或使用现有的
            group_key = self.key_manager.get_group_key(group_id)
            if not group_key:
                group_key = GroupKeyManager.generate_group_key()
                self.key_manager.set_group_key(group_id, group_key)
            
            # 使用被邀请用户的公钥加密群组密钥
            encrypted_group_key = self.key_manager.encrypt_for_user(
                group_key, 
                invitee_public_key
            )
            
            result = self.network.invite_to_group(
                group_id=group_id,
                username=username,
                encrypted_group_key=encrypted_group_key.hex()
            )
            
            if result.get('success'):
                QMessageBox.information(self, "成功", f"已向 {username} 发送邀请")
            else:
                QMessageBox.critical(self, "错误", result.get('error', '邀请失败'))
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
    
    def _view_invitations(self):
        """查看待处理的邀请"""
        result = self.network.get_groups()
        if not result.get('success'):
            QMessageBox.warning(self, "错误", result.get('error', '获取邀请失败'))
            return
        
        invitations = result.get('invitations', [])
        if not invitations:
            QMessageBox.information(self, "提示", "没有待处理的邀请")
            return
        
        # 创建邀请列表对话框
        from PyQt6.QtWidgets import QDialog, QListWidget, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("待处理邀请")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        list_widget = QListWidget()
        for inv in invitations:
            item = QListWidgetItem(
                f"📨 {inv.get('inviter_name', '未知')} 邀请您加入群组: {inv.get('group_name', '未知群组')}"
            )
            item.setData(Qt.ItemDataRole.UserRole, inv)
            list_widget.addItem(item)
        
        layout.addWidget(list_widget)
        
        btn_layout = QHBoxLayout()
        accept_btn = QPushButton("✅ 接受")
        reject_btn = QPushButton("❌ 拒绝")
        close_btn = QPushButton("关闭")
        
        def accept_invitation():
            current = list_widget.currentItem()
            if not current:
                return
            inv = current.data(Qt.ItemDataRole.UserRole)
            result = self.network.respond_invitation(inv['id'], accept=True)
            if result.get('success'):
                QMessageBox.information(dialog, "成功", "已加入群组")
                list_widget.takeItem(list_widget.row(current))
                if list_widget.count() == 0:
                    dialog.close()
            else:
                QMessageBox.warning(dialog, "错误", result.get('error', '操作失败'))
        
        def reject_invitation():
            current = list_widget.currentItem()
            if not current:
                return
            inv = current.data(Qt.ItemDataRole.UserRole)
            result = self.network.respond_invitation(inv['id'], accept=False)
            if result.get('success'):
                QMessageBox.information(dialog, "成功", "已拒绝邀请")
                list_widget.takeItem(list_widget.row(current))
                if list_widget.count() == 0:
                    dialog.close()
            else:
                QMessageBox.warning(dialog, "错误", result.get('error', '操作失败'))
        
        accept_btn.clicked.connect(accept_invitation)
        reject_btn.clicked.connect(reject_invitation)
        close_btn.clicked.connect(dialog.close)
        
        btn_layout.addWidget(accept_btn)
        btn_layout.addWidget(reject_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()
    
    def _show_group_menu(self):
        """显示群组管理菜单"""
        menu = QMenu(self)
        menu.addAction("👥 创建群组", self._create_group)
        menu.addAction("📨 邀请用户", self._invite_to_group)
        menu.addAction("📬 查看邀请", self._view_invitations)
        menu.addSeparator()
        menu.addAction("🔄 刷新群组", self._nav_groups)
        menu.exec(self.sender().mapToGlobal(self.sender().rect().bottomLeft()))
    
    def _do_logout(self):
        """退出登录"""
        reply = QMessageBox.question(
            self, "确认退出", "确定要退出登录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # 锁定密钥
            self.key_manager.lock()
            # 发出退出信号
            self.logout_requested.emit()
            # 关闭当前窗口
            self.close()
    
    def _change_password(self):
        """修改密码"""
        from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle("修改密码")
        dialog.setFixedSize(400, 280)
        
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        
        old_pwd = QLineEdit()
        old_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        old_pwd.setPlaceholderText("输入当前密码")
        form.addRow("当前密码:", old_pwd)
        
        new_pwd = QLineEdit()
        new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        new_pwd.setPlaceholderText("输入新密码")
        form.addRow("新密码:", new_pwd)
        
        confirm_pwd = QLineEdit()
        confirm_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_pwd.setPlaceholderText("确认新密码")
        form.addRow("确认密码:", confirm_pwd)
        
        layout.addLayout(form)
        layout.addSpacing(20)
        
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        confirm_btn = QPushButton("确认修改")
        confirm_btn.setStyleSheet("background: #1a73e8; color: white; padding: 8px 16px;")
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)
        
        def do_change():
            old_password = old_pwd.text()
            new_password = new_pwd.text()
            confirm_password = confirm_pwd.text()
            
            if not old_password or not new_password:
                QMessageBox.warning(dialog, "提示", "请填写所有字段")
                return
            
            if new_password != confirm_password:
                QMessageBox.warning(dialog, "提示", "两次输入的新密码不一致")
                return
            
            # 验证密码强度
            from auth.password import PasswordManager
            valid, msg = PasswordManager.validate_password(new_password)
            if not valid:
                QMessageBox.warning(dialog, "提示", msg)
                return
            
            # 验证旧密码
            password_prehash = PasswordManager.prehash_password(old_password)
            result = self.network.login_password(
                self.key_manager.user_keys.username, password_prehash
            )
            
            if not result.get('success'):
                QMessageBox.critical(dialog, "错误", "当前密码错误")
                return
            
            # 准备新密码数据
            try:
                reset_data = self.key_manager.prepare_password_reset(new_password)
                
                # 发送密码修改请求
                reset_result = self.network.reset_password(
                    username=self.key_manager.user_keys.username,
                    recovery_key=None,
                    new_password_hash=reset_data['new_password_hash'],
                    new_encrypted_master_key=reset_data['new_encrypted_master_key'],
                    new_master_key_salt=reset_data['new_master_key_salt']
                )
                
                if reset_result.get('success'):
                    # 自动解除设备信任（密码已更改）
                    if self.device_trust and self.key_manager.user_keys:
                        email = self.key_manager.user_keys.email
                        if email:
                            self.device_trust.clear_trust(email)
                    
                    QMessageBox.information(dialog, "成功", "密码修改成功，请使用新密码重新登录")
                    dialog.accept()
                    # 触发退出登录
                    self.key_manager.lock()
                    self.logout_requested.emit()
                    self.close()
                else:
                    QMessageBox.critical(dialog, "错误", reset_result.get('error', '密码修改失败'))
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"密码修改失败: {str(e)}")
        
        confirm_btn.clicked.connect(do_change)
        dialog.exec()
    
    def _revoke_device_trust(self):
        """解除设备信任"""
        from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit
        
        if not self.device_trust:
            QMessageBox.warning(self, "提示", "设备信任功能不可用")
            return
        
        email = self.key_manager.user_keys.email if self.key_manager.user_keys else ""
        
        if not self.device_trust.has_trusted_device(email):
            QMessageBox.information(self, "提示", "当前用户未信任此设备")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("解除设备信任")
        dialog.setFixedSize(400, 200)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel(f"确认解除此设备对账号 {email} 的信任？\n解除后，下次登录需要密码。"))
        layout.addSpacing(10)
        
        form = QFormLayout()
        pwd_input = QLineEdit()
        pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        pwd_input.setPlaceholderText("输入密码以确认")
        form.addRow("密码验证:", pwd_input)
        layout.addLayout(form)
        
        layout.addSpacing(10)
        
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        confirm_btn = QPushButton("确认解除")
        confirm_btn.setStyleSheet("background: #f57c00; color: white; padding: 8px 16px;")
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)
        
        def do_revoke():
            password = pwd_input.text()
            if not password:
                QMessageBox.warning(dialog, "提示", "请输入密码")
                return
            
            # 验证密码
            from auth.password import PasswordManager
            password_prehash = PasswordManager.prehash_password(password)
            result = self.network.login_password(
                self.key_manager.user_keys.username, password_prehash
            )
            
            if not result.get('success'):
                QMessageBox.critical(dialog, "错误", "密码错误")
                return
            
            # 解除信任
            self.device_trust.clear_trust(email)
            QMessageBox.information(dialog, "成功", "设备信任已解除")
            dialog.accept()
        
        confirm_btn.clicked.connect(do_revoke)
        dialog.exec()

    def _create_breadcrumb(self):
        """创建面包屑导航"""
        # 清空现有的面包屑
        while self.breadcrumb_layout.count():
            item = self.breadcrumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 根路径
        if self.current_group_id:
            root_text = "群组空间"
        else:
            root_text = "我的云盘"

        # 如果有子路径，显示返回按钮
        if self.current_path:
            back_btn = QPushButton("← 返回上一级")
            back_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #1a73e8;
                    border: none;
                    padding: 4px 8px;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: #e8f0fe;
                    border-radius: 4px;
                }
            """)
            back_btn.clicked.connect(self._go_back)
            self.breadcrumb_layout.addWidget(back_btn)

            # 分隔符
            separator = QLabel("|")
            separator.setStyleSheet("color: #dadce0; padding: 0 8px;")
            self.breadcrumb_layout.addWidget(separator)

        # 根目录按钮
        root_btn = QPushButton(root_text)
        root_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #1a73e8;
                border: none;
                padding: 4px 8px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #e8f0fe;
                border-radius: 4px;
            }
        """)
        root_btn.clicked.connect(self._go_to_root)
        self.breadcrumb_layout.addWidget(root_btn)

        # 决定显示哪些路径（智能省略中间部分）
        path_len = len(self.current_path)
        if path_len > 0:
            # 显示最后4级（如果有的话）
            display_items = []

            if path_len <= 4:
                # 路径短，全部显示
                display_items = list(enumerate(self.current_path))
            else:
                # 路径长，显示省略号 + 最后4级
                display_items = [
                    (None, (None, "...")),  # 省略号占位
                    (path_len - 4, self.current_path[-4]),  # 倒数第4级
                    (path_len - 3, self.current_path[-3]),  # 倒数第3级
                    (path_len - 2, self.current_path[-2]),  # 倒数第2级
                    (path_len - 1, self.current_path[-1])  # 最后1级
                ]

            # 添加路径中的每个文件夹
            for idx, (folder_id, folder_name) in display_items:
                # 分隔符
                separator = QLabel("/")
                separator.setStyleSheet("color: #5f6368; padding: 0 4px; font-size: 14px;")
                self.breadcrumb_layout.addWidget(separator)

                if idx is None:
                    # 省略号（不可点击）
                    ellipsis = QLabel(folder_name)
                    ellipsis.setStyleSheet("color: #5f6368; padding: 4px 8px; font-size: 14px;")
                    self.breadcrumb_layout.addWidget(ellipsis)
                else:
                    # 文件夹按钮
                    folder_btn = QPushButton(folder_name)
                    folder_btn.setStyleSheet("""
                        QPushButton {
                            background: transparent;
                            color: #1a73e8;
                            border: none;
                            padding: 4px 8px;
                            font-size: 14px;
                            font-weight: 500;
                        }
                        QPushButton:hover {
                            background: #e8f0fe;
                            border-radius: 4px;
                        }
                    """)
                    # 使用 lambda 捕获当前索引
                    folder_btn.clicked.connect(lambda checked, i=idx: self._go_to_path(i))
                    self.breadcrumb_layout.addWidget(folder_btn)

        self.breadcrumb_layout.addStretch()

    def _go_back(self):
        """返回上一级"""
        if self.current_path:
            self.current_path.pop()
            self._create_breadcrumb()
            self._refresh_files()

    def _go_to_root(self):
        """返回根目录"""
        self.current_path = []
        self._create_breadcrumb()
        self._refresh_files()

    def _go_to_path(self, index):
        """跳转到指定路径"""
        # 保留到指定索引的路径
        self.current_path = self.current_path[:index + 1]
        self._create_breadcrumb()
        self._refresh_files()
