# MyLinspirer Proxy Server

一个Python实现的MyLinspirer MITM代理服务器

## 展示
<img width="1132" height="750" alt="image" src="https://github.com/user-attachments/assets/c417ed0e-56f3-4e27-86e7-8578280ed803" />
<img width="1130" height="752" alt="image" src="https://github.com/user-attachments/assets/0f351a19-7b4a-47cf-8120-d7e0a524e2db" />
<img width="1132" height="750" alt="image" src="https://github.com/user-attachments/assets/390c5e41-4ca5-4bc3-85e8-c1d6409bb9b3" />

## 系统要求
- Linspirer MDM v5.04
- Python 3.10+

## 安装步骤

```bash
# 安装依赖
pip install -r requirements.txt
```

## 配置说明

复制示例环境文件并填写密钥（逆向自launcher）：

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
或者：
```bash
gunicorn main:app -k uvicorn.workers.UvicornWorker -b IP:端口
```
