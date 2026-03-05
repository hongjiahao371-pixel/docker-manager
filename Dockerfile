FROM python:3.11-slim

WORKDIR /app

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
CMD ["python", "/app/app.py"]
