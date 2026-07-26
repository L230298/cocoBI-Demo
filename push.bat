@echo off
chcp 65001 >nul
echo ===================================
echo   cocoBI 推送代码到 GitHub - 自动化脚本
echo ===================================
echo.

:: ========= 1. 检查 git =========
git --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 git,请先安装: https://git-scm.com/download/win
    pause
    exit /b 1
)

:: ========= 2. 进入项目目录 =========
cd /d "%~dp0"
echo [1/7] 当前目录: %cd%
echo.

:: ========= 3. 询问 GitHub 用户名和仓库 =========
set /p GITHUB_USER="请输入您的 GitHub 用户名: "
set /p REPO_NAME="请输入仓库名(默认 coco-bi-demo): "
if "%REPO_NAME%"=="" set REPO_NAME=coco-bi-demo

set REPO_URL=https://github.com/%GITHUB_USER%/%REPO_NAME%.git
echo.
echo 将要推送到: %REPO_URL%
echo.

:: ========= 4. 配置 git 身份(如果还没配) =========
git config --global user.name >nul 2>&1
if errorlevel 1 (
    set /p GIT_NAME="请输入您的名字(英文/拼音): "
    set /p GIT_EMAIL="请输入您的邮箱: "
    git config --global user.name "%GIT_NAME%"
    git config --global user.email "%GIT_EMAIL%"
    echo.
)

:: ========= 5. .gitignore =========
if not exist .gitignore (
    echo [2/7] 创建 .gitignore ...
    (
        echo # Node
        echo node_modules/
        echo dist/
        echo .cache/
        echo.
        echo # Python
        echo __pycache__/
        echo *.pyc
        echo venv/
        echo.
        echo # 数据
        echo backend/data/uploads/*
        echo backend/data/exports/*
        echo backend/data/feedback/*
        echo !backend/data/uploads/.gitkeep
        echo.
        echo # 环境
        echo .env
        echo .env.local
        echo.
        echo # 日志
        echo *.log
        echo.
        echo # IDE
        echo .vscode/
        echo .idea/
        echo.
        echo # OS
        echo .DS_Store
        echo Thumbs.db
    ) > .gitignore
) else (
    echo [2/7] .gitignore 已存在,跳过
)
echo.

:: ========= 6. git init =========
if not exist .git (
    echo [3/7] 初始化 git 仓库 ...
    git init
) else (
    echo [3/7] git 仓库已存在,跳过
)
echo.

:: ========= 7. git add + commit =========
echo [4/7] 添加文件 ...
git add .
echo.
echo [5/7] 提交 ...
git commit -m "feat: cocoBI AI 数据分析助手 Demo"
echo.

:: ========= 8. 添加远程 + 推送 =========
git remote remove origin 2>nul
echo [6/7] 关联远程仓库 ...
git remote add origin %REPO_URL%
echo.

echo [7/7] 推送到 GitHub ...
git branch -M main
git push -u origin main
echo.

if errorlevel 1 (
    echo.
    echo ========= 推送失败 =========
    echo 常见原因:
    echo   1. 仓库不存在或没创建 → 去 https://github.com/new 创建一个空仓库
    echo   2. 认证失败 → 配置 Personal Access Token 或用 GitHub CLI
    echo   3. 详见 PUSH_COMMANDS.md
    echo.
) else (
    echo ===================================
    echo   ✓ 推送成功!
    echo ===================================
    echo.
    echo 仓库地址: %REPO_URL%
    echo.
    echo 下一步:去 Render (https://render.com) 一键部署
    echo.
)

pause
