#!/bin/bash
# cocoBI Demo - 一键启动 (Linux/macOS)
set -e

echo "===================================="
echo "  cocoBI Demo - 一键启动"
echo "===================================="
echo

# 后端
echo "[1/3] 启动后端服务 (端口 8000)..."
(cd backend && pip install -r requirements.txt && python main.py) &
BACKEND_PID=$!
sleep 3

# 前端
echo "[2/3] 启动前端服务 (端口 5173)..."
(cd frontend && npm install && npm run dev) &
FRONTEND_PID=$!
sleep 3

echo "[3/3] 打开浏览器..."
# 使用 127.0.0.1 避免某些 OS 上 localhost 解析为 IPv6 (::1) 导致无法访问
open http://127.0.0.1:5173 2>/dev/null || xdg-open http://127.0.0.1:5173 2>/dev/null || echo "请手动打开 http://127.0.0.1:5173"

echo
echo "✅ 启动完成!"
echo "   后端 API 文档: http://127.0.0.1:8000/docs"
echo "   前端界面: http://127.0.0.1:5173"
echo
echo "按 Ctrl+C 停止所有服务..."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
