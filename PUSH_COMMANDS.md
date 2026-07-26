# 推送代码到 GitHub - 复制粘贴清单

> 一步步复制粘贴命令到 PowerShell / CMD / VSCode 终端即可

## 🎯 前提:已在 GitHub 创建空仓库

1. 打开 https://github.com/new
2. 填 Repository name(如 `coco-bi-demo`)
3. **不要勾选任何初始化选项**(README / .gitignore / License)
4. 点 "Create repository"
5. 看到 "Quick setup" 页面 → 复制 **仓库 URL**(形如 `https://github.com/你的用户名/coco-bi-demo.git`)

---

## 📋 命令清单(每步复制粘贴运行)

### ⌨️ 准备工作:打开 PowerShell

按 `Win + X` → 选 "Windows PowerShell" 或 "终端"

### 步骤 1:进入项目目录

```powershell
cd C:\Users\huawei\Desktop\cocobi-demo
```

### 步骤 2:检查 Git 是否已装

```powershell
git --version
```

✅ 应该看到 `git version 2.x.x` 这种输出  
❌ 如果报错 "git 不是内部或外部命令" → 先安装: https://git-scm.com/download/win

### 步骤 3:初始化 Git 仓库

```powershell
git init
```

输出:`Initialized empty Git repository in C:/Users/huawei/Desktop/cocobi-demo/.git/`

### 步骤 4:配置身份(每个电脑只需配一次)

```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

> 把 `Your Name` 改成您的真实姓名(英文或拼音),  
> `your.email@example.com` 改成您的邮箱(用 GitHub 注册的那个)

### 步骤 5:加入 .gitignore(避免上传 node_modules 和数据)

```powershell
# 创建一个全量 .gitignore(如果还没有)
@'
# Node
node_modules/
dist/
.cache/

# Python
__pycache__/
*.pyc
backend/venv/

# 数据和上传(本地文件不上传)
backend/data/uploads/*
backend/data/exports/*
backend/data/feedback/*
!backend/data/uploads/.gitkeep
!backend/data/uploads/4960b9cc4184.xlsx

# 环境
.env
.env.local

# 日志
*.log

# IDE
.vscode/
.idea/

# 系统
.DS_Store
Thumbs.db
'@ | Out-File -Encoding utf8 .gitignore
```

> ⚠️ 注意:`4960b9cc4184.xlsx` 是您的测试数据,临时保留。如果不要,删掉那行。

### 步骤 6:全部文件加入 Git

```powershell
git add .
```

### 步骤 7:第一次提交

```powershell
git commit -m "feat: cocoBI AI 数据分析助手 Demo

- 后端: FastAPI + 4 Agent + 7 工具(mock LLM)
- 前端: React + TypeScript + Vite + ECharts
- 支持 CSV/Excel 上传 + 自然语言查询 + 数据可视化
- 部署: Render Blueprint 一键部署"
```

### 步骤 8:关联到您的 GitHub 仓库

把 `你的用户名` 替换成您实际的 GitHub 用户名:

```powershell
git remote add origin https://github.com/你的用户名/coco-bi-demo.git
```

**示例**(假设用户名 `zhangsan`):

```powershell
git remote add origin https://github.com/zhangsan/coco-bi-demo.git
```

### 步骤 9:改默认分支为 main

```powershell
git branch -M main
```

### 步骤 10:推送到 GitHub

```powershell
git push -u origin main
```

🎉 **完成!** 打开 https://github.com/你的用户名/coco-bi-demo 应该能看到代码。

---

## 🐛 如果遇到错误

### 错误 1:`remote origin already exists`

```powershell
git remote remove origin
git remote add origin https://github.com/你的用户名/coco-bi-demo.git
```

### 错误 2:`failed to push some refs` (GitHub 有东西)

```powershell
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### 错误 3:认证失败 (用户名/密码)

旧方式 `https://用户名:密码@github.com` 已废弃。需要用 **Personal Access Token (PAT)**:

1. GitHub 右上头像 → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token → 勾选 `repo` → Generate
3. 复制 token(只显示一次!)
4. 推送时:
   - Username: 您的 GitHub 用户名
   - Password: **粘贴刚才的 token**(不是密码!)

或者用 **GitHub CLI**(更简单):

```powershell
winget install GitHub.cli
gh auth login
```

### 错误 4:中文字符乱码

```powershell
git config --global core.quotepath false
git config --global i18n.commitencoding utf-8
git config --global i18n.logoutputencoding utf-8
```

---

## ✅ 推送成功后

回到 GitHub 仓库页面,刷新一下,应该能看到:
- `backend/` Python 后端代码
- `frontend/` React 前端代码
- `render.yaml` 部署配置
- `DEPLOY.md` 部署文档

---

## 🚀 下一步:用 Render 部署

1. 打开 https://render.com
2. 用 GitHub 登录
3. Dashboard → "New +" → "Blueprint"
4. 选您刚推的 `coco-bi-demo` 仓库
5. 点 "Apply" → Render 自动读 `render.yaml`
6. 等 5-8 分钟构建完成
7. 填前端环境变量 `VITE_API_BASE_URL = <后端URL>`
8. 完成!永久公网 URL 🎉

详细步骤见 [DEPLOY.md](DEPLOY.md)

---

## 💡 如果您嫌麻烦

**临时方案:Cloudflare Tunnel** 5 分钟就能用,不用 GitHub,告诉我就行!
