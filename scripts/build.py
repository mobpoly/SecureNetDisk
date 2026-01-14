import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_app(name, entry_point, is_gui=True, icon_path=None):
    print(f"\n--- Building {name} ---")
    
    # 基础命令
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",  # 目录模式
        f"--name={name}",
    ]
    
    # 添加图标
    if icon_path and os.path.exists(icon_path):
        cmd.append(f"--icon={icon_path}")
    
    if is_gui:
        cmd.append("--windowed")  # 客户端不显示控制台
    else:
        cmd.append("--console")   # 服务端显示控制台
        
    # 添加项目根目录到导入路径
    cmd.append(f"--paths={os.getcwd()}")
    
    # 添加资源文件
    resources_dir = os.path.join(os.getcwd(), "client", "resources")
    if os.path.exists(resources_dir):
        cmd.append(f"--add-data={resources_dir};client/resources")
    
    # 入口点
    cmd.append(entry_point)
    
    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print(f"--- {name} Build Complete ---")

def main():
    root_dir = Path(__file__).parent.parent
    os.chdir(root_dir)
    
    # 确保产物目录存在
    dist_dir = root_dir / "dist"
    if dist_dir.exists():
        print(f"Cleaning existing dist directory: {dist_dir}")
        shutil.rmtree(dist_dir)
    
    try:
        # 客户端图标路径
        client_icon = root_dir / "client" / "resources" / "icon.ico"
        
        # 打包客户端
        build_app("SecureDiskClient", "client/main.py", is_gui=True, icon_path=str(client_icon))
        
        # 打包服务端
        build_app("SecureDiskServer", "server/main.py", is_gui=False)
        
        print("\n" + "="*30)
        print("ALL BUILDS SUCCESSFUL")
        print(f"Output location: {dist_dir.absolute()}")
        print("="*30)
        
    except Exception as e:
        print(f"\nBUILD FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
