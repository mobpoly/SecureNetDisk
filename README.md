# 安全网络加密磁盘系统

基于 Python 的端到端加密网络磁盘系统，采用自定义安全传输协议。

## 功能特性

- 🔐 端到端加密存储（零知识架构）
- 🔑 双重登录方式（口令 / Email验证码）
- 👥 群组协作与加密共享
- 🛡️ 自定义安全传输协议
- 🎨 现代化 PyQt6 界面

## 安装

```bash
pip install -r requirements.txt
```

## 启动服务端

```bash
python -m server.main
```

## 启动客户端

```bash
python -m client.main
```

## 技术栈

- Python 3.8+
- PyQt6 (GUI)
- pycryptodome (加密算法)
- SQLite (数据库)
