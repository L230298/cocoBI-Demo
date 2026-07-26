# cocoBI 后端 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# 端口(Railway 通过 PORT 环境变量注入,默认 8000)
EXPOSE 8000

# 健康检查 - 根据实际 PORT 动态检测
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 8000)}/api/health').read()" || exit 1

# 启动(Railway 注入 PORT)
# 用 sh 显式执行,确保 $PORT 变量能正常展开
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info"]

