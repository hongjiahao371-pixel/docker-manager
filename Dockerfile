FROM python:3.11-slim

WORKDIR /app

# 安装 docker CLI (不安装dockerd，只用客户端)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && curl -fsSL https://download.docker.com/linux/static/stable/stable-amd64/docker-26.0.0.tgz | tar -xz -C /tmp/ \
    && mv /tmp/docker/docker /usr/local/bin/ \
    && rm -rf /tmp/docker \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装 docker-compose
RUN curl -fsSL "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py .
COPY templates/ ./templates/

# 暴露端口
EXPOSE 8888

# 挂载Docker socket（容器内访问宿主机Docker）
VOLUME /var/run/docker.sock:/var/run/docker.sock

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 启动应用
CMD ["gunicorn", "--bind", "0.0.0.0:8888", "--workers", "2", "--timeout", "120", "app:app"]
