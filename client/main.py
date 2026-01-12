"""
客户端主程序入口
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from client.network import NetworkClient, ServerInfo
from client.key_manager import KeyManager
from client.ui.login_dialog import LoginDialog
from client.ui.main_window import MainWindow


class Application:
    """应用程序管理器"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("安全网盘")
        self.app.setStyle("Fusion")
        
        self.server_info = ServerInfo(host="localhost", port=9000)
        self.network = NetworkClient(self.server_info)
        self.key_manager = KeyManager()
        self.main_window = None
        self.should_exit = False
    
    def run(self) -> int:
        """运行应用"""
        # 连接服务器
        print("正在连接服务器...")
        if not self.network.connect():
            QMessageBox.critical(
                None, "连接失败", 
                f"无法连接到服务器 {self.server_info.host}:{self.server_info.port}\n"
                "请确保服务器已启动。"
            )
            return 1
        
        print("连接成功")
        
        # 登录循环（支持退出后重新登录）
        while not self.should_exit:
            if not self._show_login():
                break
            
            self._show_main_window()
        
        # 清理
        self.network.disconnect()
        self.key_manager.lock()
        
        return 0
    
    def _show_login(self) -> bool:
        """显示登录对话框"""
        print("显示登录界面...")
        login = LoginDialog(self.network, self.key_manager)
        
        if login.exec() != LoginDialog.DialogCode.Accepted:
            self.should_exit = True
            return False
        
        print("登录成功")
        return True
    
    def _show_main_window(self):
        """显示主窗口"""
        print("显示主界面...")
        self.main_window = MainWindow(self.network, self.key_manager)
        self.main_window.logout_requested.connect(self._on_logout)
        self.main_window.show()
        self.app.exec()
    
    def _on_logout(self):
        """处理退出登录"""
        print("用户退出登录")
        self.main_window = None
        # 不设置 should_exit，循环会继续显示登录界面


def main():
    """主函数"""
    app = Application()
    return app.run()


if __name__ == '__main__':
    sys.exit(main())
