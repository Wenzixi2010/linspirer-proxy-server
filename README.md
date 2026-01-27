# MyLinspirer Proxy Server

一个Python实现的MyLinspirer MITM代理服务器

## 功能特性

- **代理服务器**：将请求转发到Linspirer云服务器
- **认证机制**：基于JWT的认证，使用bcrypt密码哈希
- **请求/响应拦截**：修改JSON-RPC请求和响应
- **命令队列**：管理和验证发送到设备的命令
- **请求日志**：记录所有请求和响应，便于调试
- **基于规则的拦截**：配置规则拦截和修改特定方法
- **随机应用时长**：自动修改应用使用时长记录

## 系统要求

- Python 3.10+

## 安装步骤

```bash
# 安装依赖
pip install -r requirements.txt
```

## 配置说明

复制示例环境文件并自定义：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下内容：

- `LINSPIRER_KEY`：32字节AES密钥（十六进制编码）
- `LINSPIRER_IV`：16字节AES向量（十六进制编码）
- `LINSPIRER_TARGET_URL`：目标服务器URL
- `LINSPIRER_JWT_SECRET`：JWT令牌的密钥
- `LINSPIRER_DB_PATH`：sqlite地址
- `LINSPIRER_HOST`：服务器主机地址
- `LINSPIRER_PORT`：服务器端口

## 运行

```bash
python main.py
```
```bash
或者：
gunicorn main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080
```