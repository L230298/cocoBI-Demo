#!/bin/sh
# cocoBI 后端启动脚本
# Railway / Render / 任何平台通用

# Railway 默认注入 PORT,本地开发 fallback 到 8000
PORT="${PORT:-8000}"

echo "=========================================="
echo "cocoBI Backend 启动中..."
echo "监听: 0.0.0.0:${PORT}"
echo "=========================================="

# 启动 uvicorn
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --workers 1 \
    --log-level info \
    --timeout-keep-alive 30
