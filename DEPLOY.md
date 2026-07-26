# cocoBI Demo - Render 部署指南

> 把这个 demo 永久部署到 Render 公网,获得 `https://xxx.onrender.com` 永久地址。

## 🎯 5 步部署(预计 15 分钟)

### 第 1 步:把代码推到 GitHub(5 分钟)

如果您已经有项目在 GitHub,跳过这步。

```bash
cd cocobi-demo
git init
git add .
git commit -m "feat: 添加 Render 部署配置"
# 在 github.com 新建一个 repo(比如 coco-bi-demo)
git remote add origin https://github.com/你的用户名/coco-bi-demo.git
git branch -M main
git push -u origin main
```

### 第 2 步:登录 Render(1 分钟)

访问 **https://render.com** → "Get Started for Free" → 用 **GitHub 账号登录**(授权)。

### 第 3 步:用 Blueprint 一键部署(2 分钟)

1. Dashboard 右上角点 **"New +"** → **"Blueprint"**
2. 选您刚推的 GitHub repo(比如 `cocobi-demo`)
3. Render 自动检测到 `render.yaml`,显示两个服务:
   - ✅ `cocobi-backend` (Web Service / Docker)
   - ✅ `cocobi-frontend` (Static Site)
4. 点 **"Apply"** → 开始构建

### 第 4 步:等 5-8 分钟构建完成

| 服务 | 状态 | 预期 URL |
|------|------|---------|
| `cocobi-backend` | 应显示 "Live" | `https://cocobi-backend.onrender.com` |
| `cocobi-frontend` | 应显示 "Live" | `https://cocobi-frontend.onrender.com` |

### 第 5 步:配置前端环境变量(关键!)

1. 进 `cocobi-frontend` 的 Dashboard
2. 左侧 **"Environment"**
3. 添加环境变量:
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: `https://cocobi-backend.onrender.com` ← **改成您实际的后端 URL**
4. 保存 → 自动触发 rebuild → 1-2 分钟后生效

### 🎉 完成!

打开 `https://cocobi-frontend.onrender.com` —— 任何人都能从任何网络访问!

---

## ⚠️ 注意事项

### 💤 免费层睡眠机制
- Web Service 免费层:**15 分钟无活动会休眠**,下次访问冷启动需要 30-50 秒
- Static Site:**不会休眠**
- 如果要 24×7 不休眠 → 升级到 $7/月 Starter 套餐

### 💾 数据持久性
当前后端用**内存数据库**,每次冷启动会**丢失所有上传的数据集**。
- 方案 A:接受此限制(demo 重新上传即可)
- 方案 B:升级到 Starter 套餐(有持久磁盘)
- 方案 C:接入 Postgres(超纲,暂时不做)

### 🔒 上传文件大小
免费层磁盘 1GB,`MAX_DATASET_SIZE_MB` 默认 10MB(已在 render.yaml 配置)。

### 🐛 调试
- 看 Render 的 "Logs" 标签,实时日志
- 后端 `/docs` 可以看 API 文档
- 浏览器 F12 → Console / Network 排查前端问题

---

## 📋 已创建的文件

| 文件 | 作用 |
|------|------|
| `render.yaml` | Render Blueprint 配置(根目录) |
| `backend/Dockerfile` | 后端 Docker 镜像 |
| `backend/.dockerignore` | Docker 排除项 |
| `frontend/.env.example` | 环境变量模板 |
| `frontend/src/api/client.ts` | 改用 `VITE_API_BASE_URL` 动态后端地址 |

---

## 🚀 如果您想要更简单的临时方案

**Cloudflare Tunnel** - 不需要 GitHub/Render,5 分钟搞个公网 URL:

```
npx cloudflared tunnel --url http://localhost:5180
```

会得到 `https://xxx.trycloudflare.com`,任何人可访问(**会话级临时**,关电脑就失效)。

---

## 💡 部署后的运维技巧

### 更新代码
```bash
git add .
git commit -m "update"
git push
```
Render 自动检测 → 触发重建 → 1-2 分钟后生效。

### 查看日志
Render Dashboard → 服务 → "Logs" → 实时日志。

### 自定义域名
Render 付费功能或用 Cloudflare 代理转发。

---

需要我帮您做的:
- 🚀 立刻配置 Cloudflare Tunnel(快速临时方案)
- 📝 写一版 README 给团队/老板看
- 🔍 检查部署中遇到的具体错误
