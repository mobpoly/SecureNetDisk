# 安全网络加密磁盘系统

基于 Python 的端到端加密网络磁盘系统，采用自定义安全传输协议，支持大文件流式传输。

## 功能特性

- 🔐 **端到端加密** - 零知识架构，服务器无法获取明文
- 🔑 **双重登录** - 口令登录 / Email验证码 + 设备信任
- 👥 **群组协作** - 加密共享，RSA公钥分发群组密钥
- � **文件管理** - 多级文件夹、面包屑导航
- 📤 **流式传输** - 大文件分块上传/下载，内存优化
- �🛡️ **安全协议** - DH密钥交换 + AES-256-CTR加密通道
- 🎨 **现代界面** - PyQt6 Material Design 风格

## 安装

```bash
pip install -r requirements.txt
```

## 启动

### 启动服务端
```bash
# 启动服务端 (默认端口 9000)
python -m server.main

# 启动客户端
python -m client.main
```

## 分布式部署与打包

项目支持将客户端和服务端部署在不同的机器上。

### 1. 自动化打包 (Windows)
运行以下脚本生成独立运行文件夹：
```bash
python scripts/build.py
```
打包产物将位于 `dist/SecureDiskClient` 和 `dist/SecureDiskServer`。

### 2. 配置与连接
- **服务端**: 首次运行后会生成 `server.ini`。修改 `[Network] host = 0.0.0.0` 以允许外部连接。
- **客户端**: 在登录界面打开“服务器设置”，输入服务端的 IP 地址和端口。系统会自动记录历史服务器列表。

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.8+ |
| GUI | PyQt6 |
| 加密 | PyCryptodome (AES/RSA/DH) |
| 密码 | bcrypt + SHA-256 |
| 数据库 | SQLite |
| 协议 | 自定义安全传输协议 |

## 安全特性

- **密码安全**: 客户端SHA-256预哈希 → 服务端bcrypt存储
- **文件加密**: AES-256-CBC (小文件) / AES-256-CTR (大文件)
- **通信加密**: DH密钥交换 + AES-256-CTR + HMAC-SHA256
- **群组加密**: 群组密钥通过RSA公钥加密分发

## 目录结构

```
├── client/          # 客户端 (网络、密钥管理、UI)
├── server/          # 服务端 (TCP服务器、请求处理、存储)
├── crypto/          # 加密模块 (AES/RSA/DH/HMAC/KDF)
├── protocol/        # 协议模块 (数据包、握手、安全通道)
├── auth/            # 认证模块 (用户、密码、主密钥)
└── groups/          # 群组模块 (群组管理、密钥分发)
```

## 使用说明

详细功能说明请参阅 [DOCUMENTATION.md](DOCUMENTATION.md)
