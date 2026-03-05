# Docker管理Web界面

一个简洁美观的Docker容器管理工具，支持中文界面。

## 功能特性

- 📋 列出所有容器
- 🟢 显示容器状态（运行中/已停止）
- ▶️ 启动容器
- ⏹ 停止容器
- 🔄 重启容器
- 📄 查看容器日志（支持滚动查看）
- 🌏 完整中文界面

## 技术栈

- Python Flask
- Docker Python SDK
- 原生HTML + CSS + JavaScript

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python app.py
```

访问: http://localhost:8888

## Docker部署

### 使用docker-compose（推荐）

```bash
docker-compose up -d
```

### 使用docker命令

```bash
docker build -t docker-manager .
docker run -d \
  --name docker-manager \
  -p 8888:8888 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  docker-manager
```

访问: http://localhost:8888

## 部署到极空间NAS

1. 将项目文件上传到极空间NAS
2. 在Docker管理器中创建新容器
3. 端口映射: 8888:8888
4. 挂载Docker socket: /var/run/docker.sock (宿主机) -> /var/run/docker.sock (容器)

## 注意事项

- ⚠️ 容器需要挂载 `/var/run/docker.sock` 才能管理宿主机的Docker容器
- ⚠️ 建议使用 `:ro` 只读挂载以提高安全性
- 🔄 界面每30秒自动刷新容器列表
- 📋 日志默认显示最近500行

## 截图

界面采用现代化的渐变紫色主题，支持响应式布局，可在移动设备上良好显示。

## 许可证

MIT License
