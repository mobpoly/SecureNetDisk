"""
服务器主程序入口
"""

import sys
import signal
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.config import ServerConfig
from server.tcp_server import TCPServer
from server.handler import RequestHandler


def main():
    """主函数"""
    print("=" * 50)
    print("    安全网络加密磁盘 - 服务端")
    print("=" * 50)
    
    # 创建配置
    config = ServerConfig()
    config.ensure_directories()
    
    print(f"\n[配置信息]")
    print(f"  监听地址: {config.host}:{config.port}")
    print(f"  存储路径: {config.base_path.absolute()}")
    print(f"  数据库: {config.database_path.absolute()}")
    
    # 创建处理器
    handler = RequestHandler(config)
    
    # 创建服务器
    server = TCPServer(config, handler.handle)
    
    # 注册信号处理
    def signal_handler(sig, frame):
        print("\n[Server] 收到停止信号，正在关闭...")
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动服务器
    print(f"\n[启动] 服务器正在启动...")
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == '__main__':
    main()
