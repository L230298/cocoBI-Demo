@echo off
chcp 65001 >nul
echo ====================================
echo   cocoBI Demo - 一键启动
echo ====================================
echo.

echo [1/3] 启动后端服务 (端口 8000)...
start "cocoBI-Backend" cmd /k "cd backend && pip install -r requirements.txt && python main.py"
timeout /t 5 /nobreak >nul

echo [2/3] 启动前端服务 (端口 5173)...
start "cocoBI-Frontend" cmd /k "cd frontend && npm install && npm run dev"
timeout /t 3 /nobreak >nul

echo [3/3] 打开浏览器...
start http://127.0.0.1:5173

echo.
echo ✓ 启动完成!
echo    后端 API 文档: http://127.0.0.1:8000/docs
echo    前端界面: http://127.0.0.1:5173
echo.
pause
