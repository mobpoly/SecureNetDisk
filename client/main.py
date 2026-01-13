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
from client.device_trust import DeviceTrustManager
from client.ui.login_dialog import LoginDialog
from client.ui.main_window import MainWindow


from client.config import config as app_config

class Application:
    """应用程序管理器"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("安全网盘")
        self.app.setStyle("Fusion")
        
        # 加载配置
        app_config.load()
        
        self.server_info = ServerInfo(host=app_config.host, port=app_config.port)
        self.network = NetworkClient(self.server_info)
        self.key_manager = KeyManager()
        self.device_trust = DeviceTrustManager()
        self.main_window = None
        self.should_exit = False
    
    def run(self) -> int:
        """运行应用"""
        # 不再在此处连接服务器，移动到登录对话框中处理
        
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
        login = LoginDialog(self.network, self.key_manager, self.device_trust)
        
        if login.exec() != LoginDialog.DialogCode.Accepted:
            self.should_exit = True
            return False
        
        print("登录成功")
        return True
    
    def _show_main_window(self):
        """显示主窗口"""
        print("显示主界面...")
        self.main_window = MainWindow(self.network, self.key_manager, self.device_trust)
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
