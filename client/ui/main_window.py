"""
主窗口

"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QHeaderView, QMenu, QFileDialog,
    QMessageBox, QInputDialog, QProgressDialog, QSplitter,
    QFrame, QToolBar, QStatusBar, QDialog, QApplication,
    QProgressBar
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QAction, QIcon
from pathlib import Path

from .styles import StyleSheet, Icons
import platform
import subprocess
import tempfile
import os

class BadgeButton(QPushButton):
    """带红点徽章的按钮"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._badge_count = 0
        self._badge_label = QLabel(self)
        self._badge_label.setStyleSheet("""
            QLabel {
                background-color: #ea4335;
                color: white;
                font-size: 10px;
                font-weight: bold;
                border-radius: 9px;
                min-width: 18px;
                max-width: 30px;
                min-height: 18px;
                max-height: 18px;
                padding: 0 4px;
            }
        """)
        self._badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge_label.hide()

    def set_badge(self, count: int):
        """设置徽章数量"""
        self._badge_count = count
        if count > 0:
            display = "99+" if count > 99 else str(count)
            self._badge_label.setText(display)
            self._badge_label.adjustSize()
            # 定位到按钮右上角
            self._badge_label.move(self.width() - self._badge_label.width() - 2, 2)
            self._badge_label.show()
        else:
            self._badge_label.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._badge_count > 0:
            self._badge_label.move(self.width() - self._badge_label.width() - 2, 2)

import time


class ProgressDialog(QDialog):
    """专业进度对话框 - 显示进度条、速率和取消按钮"""
    cancelled = pyqtSignal()

    def __init__(self, title: str, filename: str, total_size: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(450, 180)
        self.setModal(True)
        self.total_size = total_size
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_bytes = 0
        self._cancelled = False

        self.setStyleSheet("""
            QDialog {
                background: white;
                border-radius: 12px;
            }
            QLabel {
                color: #333;
            }
            QProgressBar {
                border: none;
                border-radius: 6px;
                background: #e8eaed;
                height: 12px;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4285f4, stop:1 #34a853);
            }
            QPushButton {
                background: #ea4335;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #d93025;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        # 文件名
        self.filename_label = QLabel(f"📄 {filename}")
        self.filename_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        layout.addWidget(self.filename_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # 状态行
        status_layout = QHBoxLayout()

        self.size_label = QLabel("0 B / 0 B")
        self.size_label.setStyleSheet("font-size: 12px; color: #666;")
        status_layout.addWidget(self.size_label)

        status_layout.addStretch()

        self.speed_label = QLabel("0 KB/s")
        self.speed_label.setStyleSheet("font-size: 12px; color: #1a73e8; font-weight: 500;")
        status_layout.addWidget(self.speed_label)

        layout.addLayout(status_layout)

        # 取消按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _format_speed(self, speed: float) -> str:
        """格式化速度"""
        if speed < 1024:
            return f"{speed:.0f} B/s"
        elif speed < 1024 * 1024:
            return f"{speed / 1024:.1f} KB/s"
        else:
            return f"{speed / 1024 / 1024:.1f} MB/s"

    def update_progress(self, current_bytes: int):
        """更新进度"""
        if self._cancelled:
            return

        # 计算百分比
        percent = int((current_bytes / self.total_size) * 100) if self.total_size > 0 else 0
        self.progress_bar.setValue(percent)

        # 更新大小显示
        self.size_label.setText(f"{self._format_size(current_bytes)} / {self._format_size(self.total_size)}")

        # 计算速率 (每0.5秒更新一次)
        now = time.time()
        if now - self.last_update_time >= 0.5:
            elapsed = now - self.last_update_time
            bytes_diff = current_bytes - self.last_bytes
            speed = bytes_diff / elapsed if elapsed > 0 else 0
            self.speed_label.setText(self._format_speed(speed))
            self.last_update_time = now
            self.last_bytes = current_bytes

        # 刷新界面
        QApplication.processEvents()

    def _on_cancel(self):
        """取消操作"""
        self._cancelled = True
        self.cancelled.emit()
        self.reject()

    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self._cancelled

    def set_complete(self):
        """设置完成状态"""
        self.progress_bar.setValue(100)
        self.speed_label.setText("完成")
        self.cancel_btn.setText("关闭")
        self.cancel_btn.setStyleSheet("background: #34a853; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: 500;")
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.accept)


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

        # 群组文件未读计数 (group_id -> count)
        self.group_file_counts = {}

        # 排序状态 - 个人网盘和群组独立
        self.personal_sort_column = 'created_at'
        self.personal_sort_ascending = False
        self.group_sort_column = 'created_at'
        self.group_sort_ascending = False

        self._init_ui()
        self._refresh_files()

        # 通知轮询定时器 (2秒 - 更实时)
        self.notification_timer = QTimer(self)
        self.notification_timer.timeout.connect(self._refresh_notifications)
        self.notification_timer.start(2000)  # 2秒轮询

        # 初始加载通知
        self._refresh_notifications()
        self._temp_preview_files = []  # 临时预览文件列表

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

        # 初始化面包屑
        self._create_breadcrumb()

    def _preview_file(self, file: FileItem):
        """预览文件（仅支持小文件）"""
        if file.is_folder:
            QMessageBox.information(self, "提示", "文件夹无法预览")
            return

        if file.size > 100 * 1024 * 1024:  # 100MB限制
            QMessageBox.warning(self, "提示", "文件超过100MB，无法预览")
            return

        import tempfile
        import subprocess
        import platform
        import os
        from pathlib import Path

        try:
            # 显示加载提示
            self.statusBar().showMessage(f"正在下载并解密 {file.name}...")
            QApplication.processEvents()

            # 创建临时目录（如果不存在的話）
            temp_dir = Path.home() / ".secure_netdisk" / "previews"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # 使用原始文件名（确保唯一性）
            original_name = file.name

            # 清理文件名（移除非法字符）
            import re
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', original_name)

            # 生成唯一的临时文件路径（避免文件名冲突）
            temp_path = temp_dir / f"preview_{file.id}_{safe_name}"

            # 如果已存在同名文件，则删除
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass

            # 下载文件到临时路径（使用原始文件名）
            download_result = self._download_file_to_temp(file, str(temp_path))

            if download_result:
                # 检查文件是否存在且大小正确
                if not temp_path.exists() or temp_path.stat().st_size == 0:
                    QMessageBox.critical(self, "错误", "预览文件生成失败")
                    return

                # 根据不同系统打开文件
                system = platform.system()

                try:
                    if system == 'Windows':
                        # Windows: 使用系统默认程序打开
                        os.startfile(str(temp_path))
                    elif system == 'Darwin':  # macOS
                        # macOS: 使用open命令，并指定原始文件名
                        subprocess.run(['open', str(temp_path)], check=True)
                    elif system == 'Linux':
                        # Linux: 使用xdg-open，这是标准方式
                        subprocess.run(['xdg-open', str(temp_path)], check=True)
                    else:
                        QMessageBox.information(self, "提示",
                                                f"文件已保存到: {temp_path}\n"
                                                f"文件大小: {temp_path.stat().st_size:,} 字节")

                    # 记录临时文件信息
                    self._temp_preview_files.append(str(temp_path))

                    # 设置清理定时器（30分钟后清理）
                    QTimer.singleShot(30 * 60 * 1000, lambda: self._clean_temp_file(str(temp_path)))

                    self.statusBar().showMessage(f"正在预览 {file.name}")

                except subprocess.CalledProcessError as e:
                    # 如果系统命令失败，显示文件路径让用户手动打开
                    QMessageBox.information(
                        self,
                        "文件已准备好",
                        f"文件已解密保存，但无法自动打开。\n\n"
                        f"路径: {temp_path}\n"
                        f"名称: {file.name}\n"
                        f"大小: {file.size:,} 字节\n\n"
                        f"请手动用相关程序打开此文件。"
                    )
                except Exception as e:
                    QMessageBox.warning(self, "打开失败",
                                        f"无法自动打开文件，错误: {str(e)}\n\n"
                                        f"文件已保存到: {temp_path}")

            else:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except:
                        pass
                QMessageBox.critical(self, "错误", "文件预览失败")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"预览失败: {str(e)}")
            self.statusBar().showMessage("预览失败")

    def _download_file_to_temp(self, file: FileItem, temp_path: str) -> bool:
        """下载文件到临时路径（无进度对话框）"""
        try:
            import gc
            import base64
            import tempfile
            from pathlib import Path

            # 开始下载 - 获取元数据
            result = self.network.download_file_start(file.id)

            if not result.get('success'):
                return False

            download_id = result['download_id']
            total_size = result['size']
            encrypted_file_key = bytes.fromhex(result['encrypted_file_key'])

            del result
            gc.collect()

            # 创建临时文件接收数据
            temp_fd, temp_enc_path = tempfile.mkstemp(suffix='.enc')

            try:
                downloaded = 0
                chunk_size = 256 * 1024  # 256KB per chunk

                with os.fdopen(temp_fd, 'wb') as temp_file:
                    while True:
                        # 请求下一块数据
                        chunk_result = self.network.download_file_data(download_id, chunk_size)

                        if not chunk_result.get('success'):
                            return False

                        # 解码并写入文件
                        chunk_data = base64.b64decode(chunk_result['data'])
                        temp_file.write(chunk_data)

                        downloaded += len(chunk_data)

                        # 检查是否完成
                        if chunk_result.get('is_complete', False):
                            break

                gc.collect()

                # 解密文件密钥
                from client.file_crypto import FileCrypto

                if self.current_group_id:
                    file_key = self.key_manager.decrypt_with_group_key(
                        self.current_group_id, encrypted_file_key
                    )
                else:
                    file_key = self.key_manager.decrypt_file_key(encrypted_file_key)

                # 流式解密到目标文件
                FileCrypto.decrypt_from_encrypted_file(
                    Path(temp_enc_path),
                    file_key,
                    Path(temp_path)
                )
                gc.collect()

                return True

            finally:
                # 清理加密的临时文件
                try:
                    os.unlink(temp_enc_path)
                except:
                    pass

        except Exception as e:
            print(f"[Preview] 下载失败: {e}")
            return False

    def _clean_temp_file(self, file_path: str):
        """清理临时预览文件"""
        try:
            import os
            if os.path.exists(file_path):
                os.unlink(file_path)
                if file_path in self._temp_preview_files:
                    self._temp_preview_files.remove(file_path)
        except Exception as e:
            print(f"[Preview] 清理临时文件失败: {e}")

    def closeEvent(self, event):
        """关闭窗口时清理所有临时预览文件"""
        import os
        for temp_file in self._temp_preview_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        self._temp_preview_files.clear()
        super().closeEvent(event)

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

        self.nav_groups = BadgeButton(f"{Icons.GROUP} 共享群组")
        self.nav_groups.setCheckable(True)
        self.nav_groups.clicked.connect(self._nav_groups)
        layout.addWidget(self.nav_groups)

        # 邀请按钮（带徽章）
        self.nav_invitations = BadgeButton(f"{Icons.INVITE} 邀请通知")
        self.nav_invitations.clicked.connect(self._view_invitations)
        layout.addWidget(self.nav_invitations)

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
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # 禁用双击编辑
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

        # 添加预览选项（仅对文件且小于100MB）
        if not file.is_folder and file.size <= 100 * 1024 * 1024:
            menu.addAction(f"👁️ 预览", lambda: self._preview_file(file))
            menu.addSeparator()

        if not file.is_folder:
            menu.addAction(f"{Icons.DOWNLOAD} 下载", lambda: self._download_file(file))

        menu.addAction(f"{Icons.RENAME} 重命名", lambda: self._rename_file(file))
        menu.addAction(f"{Icons.DELETE} 删除", lambda: self._delete_file(file))

        menu.exec(self.file_table.viewport().mapToGlobal(pos))
    
    def _refresh_files(self):
        """刷新文件列表"""
        # current_path 存储 (id, name) 元组，需要提取 id
        parent_id = self.current_path[-1][0] if self.current_path else None
        result = self.network.get_file_list(parent_id=parent_id, group_id=self.current_group_id)
        
        if result.get('success'):
            self.files = [FileItem(f) for f in result.get('files', [])]
            self._update_file_table()
        else:
            self.statusBar().showMessage(f"刷新失败: {result.get('error', '未知错误')}")
    
    def _update_file_table(self):
        """更新文件表格"""
        # 排序文件列表
        self._sort_files()
        
        # 获取当前排序状态
        if self.current_group_id:
            sort_col = self.group_sort_column
            sort_asc = self.group_sort_ascending
        else:
            sort_col = self.personal_sort_column
            sort_asc = self.personal_sort_ascending
        
        # 生成排序指示符
        def get_header(label, col):
            if sort_col == col:
                arrow = "▲" if sort_asc else "▼"
                return f"{label} {arrow}"
            return label
        
        # 显示垂直表头 (行号)
        self.file_table.verticalHeader().setVisible(True)
        self.file_table.verticalHeader().setDefaultSectionSize(35)
        
        # 根据是否在群组中设置列数
        if self.current_group_id:
            self.file_table.setColumnCount(4)
            headers = [
                get_header("名称", "name"),
                get_header("上传者", "uploader_name"),
                get_header("大小", "size"),
                get_header("上传时间", "created_at")
            ]
            self.file_table.setHorizontalHeaderLabels(headers)
            self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            self.file_table.setColumnWidth(1, 120)
            self.file_table.setColumnWidth(2, 100)
            self.file_table.setColumnWidth(3, 160)
        else:
            self.file_table.setColumnCount(3)
            headers = [
                get_header("名称", "name"),
                get_header("大小", "size"),
                get_header("上传时间", "created_at")
            ]
            self.file_table.setHorizontalHeaderLabels(headers)
            self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self.file_table.setColumnWidth(1, 100)
            self.file_table.setColumnWidth(2, 160)
        
        # 连接表头点击信号 (先断开再连接，防止重复连接)
        try:
            self.file_table.horizontalHeader().sectionClicked.disconnect(self._on_header_clicked)
        except:
            pass
        self.file_table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        
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
    
    def _sort_files(self):
        """排序文件列表"""
        # 获取当前排序状态
        if self.current_group_id:
            sort_col = self.group_sort_column
            sort_asc = self.group_sort_ascending
        else:
            sort_col = self.personal_sort_column
            sort_asc = self.personal_sort_ascending
        
        # 文件夹始终在前
        folders = [f for f in self.files if f.is_folder]
        files = [f for f in self.files if not f.is_folder]
        
        # 根据排序列和方向排序
        key_func = {
            'name': lambda x: x.name.lower(),
            'size': lambda x: x.size,
            'created_at': lambda x: x.created_at or '',
            'uploader_name': lambda x: (x.uploader_name or '').lower()
        }.get(sort_col, lambda x: x.created_at or '')
        
        folders.sort(key=key_func, reverse=not sort_asc)
        files.sort(key=key_func, reverse=not sort_asc)
        
        self.files = folders + files
    
    def _on_header_clicked(self, logical_index: int):
        """处理表头点击排序"""
        # 映射列索引到排序字段
        if self.current_group_id:
            columns = {0: 'name', 1: 'uploader_name', 2: 'size', 3: 'created_at'}
            col = columns.get(logical_index)
            if col:
                if self.group_sort_column == col:
                    self.group_sort_ascending = not self.group_sort_ascending
                else:
                    self.group_sort_column = col
                    self.group_sort_ascending = False
                self._update_file_table()
        else:
            columns = {0: 'name', 1: 'size', 2: 'created_at'}
            col = columns.get(logical_index)
            if col:
                if self.personal_sort_column == col:
                    self.personal_sort_ascending = not self.personal_sort_ascending
                else:
                    self.personal_sort_column = col
                    self.personal_sort_ascending = False
                self._update_file_table()
    
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
                # 存储 (id, name) 元组
                self.current_path.append((file.id, file.name))
                self._create_breadcrumb()
                self._refresh_files()
    
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

        # 显示路径
        path_len = len(self.current_path)
        if path_len > 0:
            display_items = []
            if path_len <= 4:
                display_items = list(enumerate(self.current_path))
            else:
                display_items = [
                    (None, (None, "...")),
                    (path_len - 3, self.current_path[-3]),
                    (path_len - 2, self.current_path[-2]),
                    (path_len - 1, self.current_path[-1])
                ]

            for idx, (folder_id, folder_name) in display_items:
                separator = QLabel("/")
                separator.setStyleSheet("color: #5f6368; padding: 0 4px; font-size: 14px;")
                self.breadcrumb_layout.addWidget(separator)

                if idx is None:
                    ellipsis = QLabel(folder_name)
                    ellipsis.setStyleSheet("color: #5f6368; padding: 4px 8px; font-size: 14px;")
                    self.breadcrumb_layout.addWidget(ellipsis)
                else:
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
        self.current_path = self.current_path[:index + 1]
        self._create_breadcrumb()
        self._refresh_files()
    
    def _refresh_notifications(self):
        """刷新通知徽章"""
        try:
            result = self.network.get_notification_counts()
            if result.get('success'):
                invitation_count = result.get('invitation_count', 0)
                file_count = result.get('file_count', 0)
                # JSON 返回的 key 是字符串，需要转换为整数
                raw_counts = result.get('group_file_counts', {})
                self.group_file_counts = {int(k): v for k, v in raw_counts.items()}
                
                # 更新徽章
                self.nav_invitations.set_badge(invitation_count)
                self.nav_groups.set_badge(file_count)
        except Exception as e:
            print(f"[MainWindow] 刷新通知失败: {e}")
    
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
        # 刷新通知确保徽章是最新的
        self._refresh_notifications()
        
        result = self.network.get_groups()
        if not result.get('success'):
            QMessageBox.warning(self, "错误", result.get('error', '获取群组失败'))
            return
        
        groups = result.get('groups', [])
        if not groups:
            QMessageBox.information(self, "提示", "您还没有加入任何群组")
            return
        
        # 创建群组选择对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("选择群组")
        dialog.setMinimumSize(700, 500)
        
        layout = QHBoxLayout(dialog)
        layout.setSpacing(16)
        
        # 左侧：群组列表
        left_panel = QFrame()
        left_panel.setStyleSheet("""
            QFrame { background: #f8f9fa; border-radius: 8px; }
        """)
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("📂 我的群组"))
        
        group_list = QListWidget()
        group_list.setStyleSheet("""
            QListWidget { 
                border: none; 
                background: transparent; 
                font-size: 14px;
            }
            QListWidget::item { 
                padding: 12px 16px; 
                border-radius: 8px;
                margin: 4px 8px;
            }
            QListWidget::item:hover { background: #e8eaed; }
            QListWidget::item:selected { background: #e8f0fe; color: #1a73e8; }
        """)
        
        for g in groups:
            group_id = g['id']
            unread_count = self.group_file_counts.get(group_id, 0)
            
            # 显示未读徽章
            if unread_count > 0:
                badge = f" 🔴 {unread_count}" if unread_count <= 99 else " 🔴 99+"
                item = QListWidgetItem(f"👥 {g['name']}{badge}")
            else:
                item = QListWidgetItem(f"👥 {g['name']}")
            
            item.setData(Qt.ItemDataRole.UserRole, g)
            group_list.addItem(item)
        
        left_layout.addWidget(group_list)
        layout.addWidget(left_panel, 1)
        
        # 右侧：成员列表
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame { background: #ffffff; border: 1px solid #dadce0; border-radius: 8px; }
        """)
        right_layout = QVBoxLayout(right_panel)
        
        member_title = QLabel("👤 群组成员")
        member_title.setStyleSheet("font-size: 16px; font-weight: 500; padding: 8px;")
        right_layout.addWidget(member_title)
        
        member_list = QListWidget()
        member_list.setStyleSheet("""
            QListWidget { border: none; }
            QListWidget::item { padding: 10px 16px; border-bottom: 1px solid #e8eaed; }
        """)
        right_layout.addWidget(member_list)
        
        # 群组信息
        group_info = QLabel("")
        group_info.setStyleSheet("color: #666; font-size: 12px; padding: 8px;")
        group_info.setWordWrap(True)
        right_layout.addWidget(group_info)
        
        layout.addWidget(right_panel, 1)
        
        # 选择群组时更新成员列表
        def update_members():
            current = group_list.currentItem()
            if not current:
                return
            group = current.data(Qt.ItemDataRole.UserRole)
            group_id = group['id']
            
            # 获取成员
            members_result = self.network.get_group_members(group_id)
            member_list.clear()
            
            if members_result.get('success'):
                members = members_result.get('members', [])
                for m in members:
                    # 获取用户名（尝试多个可能的字段名）
                    username = m.get('username') or m.get('name') or m.get('user_name') or f"用户{m.get('id', '?')}"
                    is_owner = m.get('role') == 'owner'
                    role_text = "组长" if is_owner else "成员"
                    
                    if is_owner:
                        text = f"👑 {username} ({role_text})"
                    else:
                        text = f"👤 {username} ({role_text})"
                    
                    item = QListWidgetItem(text)
                    if is_owner:
                        item.setBackground(Qt.GlobalColor.yellow)
                    if m.get('email'):
                        item.setToolTip(f"邮箱: {m.get('email')}")
                    member_list.addItem(item)
                
                group_info.setText(f"群组: {group['name']}\n成员数: {len(members)}")
            else:
                group_info.setText("无法获取成员信息")
        
        group_list.currentItemChanged.connect(lambda: update_members())
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        # 邀请按钮
        def invite_to_selected_group():
            current = group_list.currentItem()
            if current:
                group = current.data(Qt.ItemDataRole.UserRole)
                self._invite_to_group(group['id'], group['name'])
        
        invite_btn = QPushButton("📨 邀请用户")
        invite_btn.setStyleSheet("background: #34a853; color: white; padding: 8px 16px; border-radius: 4px;")
        invite_btn.clicked.connect(invite_to_selected_group)
        btn_layout.addWidget(invite_btn)
        
        select_btn = QPushButton("进入群组")
        select_btn.setStyleSheet("background: #1a73e8; color: white; padding: 8px 24px; border-radius: 4px;")
        select_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(select_btn)
        
        # 将按钮添加到右侧面板底部
        right_layout.addLayout(btn_layout)
        
        # 默认选中第一个
        if group_list.count() > 0:
            group_list.setCurrentRow(0)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            current = group_list.currentItem()
            if current:
                group = current.data(Qt.ItemDataRole.UserRole)
                self.current_group_id = group['id']
                self.current_path = []
                self._create_breadcrumb()
                
                # 加载群组密钥
                self._load_group_key(group['id'])
                
                # 标记该群组的新文件通知为已读
                self.network.mark_notification_read('new_file', group['id'])
                self._refresh_notifications()
                
                self._refresh_files()
    
    def _load_group_key(self, group_id: int):
        """加载群组密钥"""
        try:
            result = self.network.get_group_key(group_id)
            if result.get('success'):
                encrypted_group_key_hex = result.get('encrypted_group_key')
                if encrypted_group_key_hex:
                    encrypted_group_key = bytes.fromhex(encrypted_group_key_hex)
                    # 使用私钥解密群组密钥 (RSA)
                    group_key = self.key_manager.decrypt_for_me(encrypted_group_key)
                    self.key_manager.set_group_key(group_id, group_key)
                    print(f"[MainWindow] 群组密钥加载成功: group_id={group_id}")
                else:
                    print(f"[MainWindow] 群组密钥为空: group_id={group_id}")
            else:
                print(f"[MainWindow] 获取群组密钥失败: {result.get('error')}")
        except Exception as e:
            print(f"[MainWindow] 加载群组密钥失败: {e}")
    
    def _upload_file(self):
        """上传文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if not file_path:
            return
        
        path = Path(file_path)
        file_size = path.stat().st_size
        temp_file_path = None
        
        try:
            import gc
            import os
            from client.file_crypto import FileCrypto
            
            # 显示加密进度提示
            self.statusBar().showMessage(f"正在加密 {path.name}...")
            QApplication.processEvents()
            
            # 加密文件
            file_key = FileCrypto.generate_file_key()
            encrypted_result, _ = FileCrypto.encrypt_file(path, file_key)
            gc.collect()
            
            # 判断返回的是字节数据还是临时文件路径
            if isinstance(encrypted_result, str):
                # 大文件：返回的是临时文件路径
                temp_file_path = encrypted_result
                total_size = os.path.getsize(temp_file_path)
                use_temp_file = True
            else:
                # 小文件：返回的是字节数据
                encrypted_data = encrypted_result
                total_size = len(encrypted_data)
                use_temp_file = False
            
            # 创建进度对话框
            progress = ProgressDialog("上传文件", path.name, total_size, self)
            progress.show()
            
            # 根据是否是群组文件选择加密方式
            if self.current_group_id:
                encrypted_file_key = self.key_manager.encrypt_with_group_key(
                    self.current_group_id, file_key
                )
            else:
                encrypted_file_key = self.key_manager.encrypt_file_key(file_key)
            
            # 开始上传
            result = self.network.upload_file_start(
                filename=path.name,
                size=total_size,
                encrypted_file_key=encrypted_file_key.hex(),
                parent_id=self.current_path[-1][0] if self.current_path else None,
                group_id=self.current_group_id
            )
            
            if not result.get('success'):
                progress.close()
                QMessageBox.critical(self, "错误", result.get('error', '上传失败'))
                return
            
            upload_id = result['upload_id']
            chunk_size = 256 * 1024  # 256KB chunks
            uploaded = 0
            
            if use_temp_file:
                # 大文件：从临时文件流式读取上传
                with open(temp_file_path, 'rb') as f:
                    while True:
                        if progress.is_cancelled():
                            # 通知服务器取消上传
                            self.network.upload_file_cancel(upload_id)
                            self.statusBar().showMessage("上传已取消")
                            return
                        
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        
                        self.network.upload_file_data(upload_id, chunk)
                        uploaded += len(chunk)
                        progress.update_progress(uploaded)
            else:
                # 小文件：从内存读取上传
                for i in range(0, total_size, chunk_size):
                    if progress.is_cancelled():
                        # 通知服务器取消上传
                        self.network.upload_file_cancel(upload_id)
                        del encrypted_data
                        gc.collect()
                        self.statusBar().showMessage("上传已取消")
                        return
                    
                    chunk = encrypted_data[i:i+chunk_size]
                    self.network.upload_file_data(upload_id, chunk)
                    uploaded += len(chunk)
                    progress.update_progress(uploaded)
                
                del encrypted_data
                gc.collect()
            
            # 结束上传
            result = self.network.upload_file_end(upload_id)
            
            if result.get('success'):
                progress.set_complete()
                progress.exec()
                self.statusBar().showMessage("上传成功")
                self._refresh_files()
            else:
                progress.close()
                QMessageBox.critical(self, "错误", result.get('error', '上传失败'))
                
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
        finally:
            # 清理临时文件
            if temp_file_path:
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
    
    def _download_file(self, file: FileItem):
        """下载文件 (流式下载)"""
        save_path, _ = QFileDialog.getSaveFileName(self, "保存文件", file.name)
        if not save_path:
            return
        
        try:
            import gc
            import base64
            import tempfile
            from pathlib import Path
            
            # 显示下载状态
            self.statusBar().showMessage(f"正在下载 {file.name}...")
            QApplication.processEvents()
            
            # 开始下载 - 获取元数据
            result = self.network.download_file_start(file.id)
            
            if not result.get('success'):
                QMessageBox.critical(self, "错误", result.get('error', '下载失败'))
                return
            
            download_id = result['download_id']
            total_size = result['size']
            encrypted_file_key = bytes.fromhex(result['encrypted_file_key'])
            
            del result
            gc.collect()
            
            # 创建进度对话框
            progress = ProgressDialog("下载文件", file.name, total_size, self)
            progress.show()
            
            # 创建临时文件接收数据
            temp_fd, temp_path = tempfile.mkstemp(suffix='.download')
            
            try:
                downloaded = 0
                chunk_size = 256 * 1024  # 256KB per chunk
                
                with open(temp_path, 'wb') as temp_file:
                    while True:
                        if progress.is_cancelled():
                            self.statusBar().showMessage("下载已取消")
                            return
                        
                        # 请求下一块数据
                        chunk_result = self.network.download_file_data(download_id, chunk_size)
                        
                        if not chunk_result.get('success'):
                            progress.close()
                            QMessageBox.critical(self, "错误", chunk_result.get('error', '下载数据失败'))
                            return
                        
                        # 解码并写入文件
                        chunk_data = base64.b64decode(chunk_result['data'])
                        temp_file.write(chunk_data)
                        
                        downloaded += len(chunk_data)
                        progress.update_progress(downloaded)
                        QApplication.processEvents()
                        
                        # 检查是否完成
                        if chunk_result.get('is_complete', False):
                            break
                        
                        del chunk_data
                        del chunk_result
                
                gc.collect()
                
                # 解密文件密钥
                from client.file_crypto import FileCrypto
                
                if self.current_group_id:
                    file_key = self.key_manager.decrypt_with_group_key(
                        self.current_group_id, encrypted_file_key
                    )
                else:
                    file_key = self.key_manager.decrypt_file_key(encrypted_file_key)
                
                # 流式解密：从临时文件直接解密到目标文件，不加载整个文件到内存
                FileCrypto.decrypt_from_encrypted_file(Path(temp_path), file_key, Path(save_path))
                gc.collect()
                
                progress.set_complete()
                progress.exec()
                self.statusBar().showMessage("下载成功")
                
            finally:
                # 清理临时文件
                try:
                    import os
                    os.close(temp_fd)
                    os.unlink(temp_path)
                except:
                    pass
            
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
    
    def _create_folder(self):
        """创建文件夹"""
        name, ok = QInputDialog.getText(self, "新建文件夹", "文件夹名称:")
        if ok and name:
            result = self.network.create_folder(
                name=name,
                parent_id=self.current_path[-1][0] if self.current_path else None,
                group_id=self.current_group_id
            )
            if result.get('success'):
                self._refresh_files()
            else:
                QMessageBox.critical(self, "错误", result.get('error', '创建失败'))
    
    def _rename_file(self, file: FileItem):
        """重命名文件"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("重命名")
        dialog.setMinimumWidth(450)  # 设置最小宽度避免遮挡文件名
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("新名称:"))
        
        name_input = QLineEdit(file.name)
        name_input.selectAll()
        layout.addWidget(name_input)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text().strip()
            if name and name != file.name:
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
            try:
                # 生成群组密钥
                group_key = self.key_manager.generate_group_key()
                
                # 使用自己的公钥加密群组密钥 (RSA)
                encrypted_group_key = self.key_manager.encrypt_for_user(
                    group_key, self.key_manager.user_keys.public_key
                )
                
                result = self.network.create_group(name, encrypted_group_key.hex())
                if result.get('success'):
                    group_id = result.get('group_id')
                    # 保存群组密钥到本地
                    self.key_manager.set_group_key(group_id, group_key)
                    QMessageBox.information(self, "成功", f"群组 {name} 创建成功")
                else:
                    QMessageBox.critical(self, "错误", result.get('error', '创建失败'))
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建群组失败: {e}")
    
    def _invite_to_group(self, group_id: int = None, group_name: str = None):
        """邀请用户加入群组"""
        # 如果没有传入 group_id，则需要先选择群组
        if group_id is None:
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
            
            # 获取群组密钥（如果本地没有则从服务器加载）
            group_key = self.key_manager.get_group_key(group_id)
            if not group_key:
                # 从服务器加载群组密钥
                self._load_group_key(group_id)
                group_key = self.key_manager.get_group_key(group_id)
                
            if not group_key:
                QMessageBox.critical(self, "错误", "无法获取群组密钥")
                return
            
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
        # 标记邀请通知为已读
        self.network.mark_notification_read('invitation')
        self._refresh_notifications()
        
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
                # 解密并保存群组密钥
                try:
                    encrypted_group_key_hex = inv.get('encrypted_group_key')
                    if encrypted_group_key_hex:
                        encrypted_group_key = bytes.fromhex(encrypted_group_key_hex)
                        group_key = self.key_manager.decrypt_for_me(encrypted_group_key)
                        group_id = inv.get('group_id')
                        self.key_manager.set_group_key(group_id, group_key)
                        print(f"[MainWindow] 群组密钥已保存: group_id={group_id}")
                except Exception as e:
                    print(f"[MainWindow] 保存群组密钥失败: {e}")
                
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
