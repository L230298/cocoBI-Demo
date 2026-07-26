# Railway 部署指南(cocobi-Demo)

> Render / Vercel / Netlify 都不可达,只有 Railway 通。我们用它!

## 🎯 5 步部署(预计 10 分钟)

### 第 1 步:登录 Railway(1 分钟)
访问 **https://railway.app** → 点 **"Login"** → 选 **"Login with GitHub"**

### 第 2 步:从 GitHub 部署后端(2 分钟)
1. Dashboard 右上点 **"New Project"**
2. 选 **"Deploy from GitHub repo"**
3. 选 **"L230298/cocoBI-Demo"** 仓库
4. **重要**:首次它会让您选 `root directory`,输入 **`backend`** ← 关键!
5. Railway 自动检测 Python → 自动构建
6. 等构建完成(2-4 分钟)

### 第 3 步:配置后端环境变量(1 分钟)
进入后端服务的 **Variables** 标签:
```
PYTHONUNBUFFERED=1
LLM_MOCK_DELAY_MS=0
MAX_DATASET_SIZE_MB=10
```

### 第 4 步:获取后端 URL
进入后端服务 → **Settings** → **Networking** → 点 **"Generate Domain"**
会得到类似:`https://cocobi-backend-production-xxx.up.railway.app`

### 第 5 步:部署前端 + 配置环境变量(3 分钟)
1. 同样方式:**New Project** → 选仓库 → **root directory = `frontend`**
2. 添加环境变量:
   - `VITE_API_BASE_URL` = 刚才的后端 URL
3. 等构建完成

### 🎉 完成!

- 后端 API:`https://cocobi-backend-production-xxx.up.railway.app`
- 前端:`https://cocobi-frontend-production-xxx.up.railway.app`
- API 文档:`https://cocobi-backend-xxx.up.railway.app/docs`

---

## ⚠️ Railway 注意事项

### 💰 费用
- 免费额度:**每月 $5**(约 500 小时)
- 后端 24×7 运行:~$7-8/月(超出免费)
- Demo 用完就关 → 不会超

### 💾 数据持久化
- 数据库是**内存的**,服务重启会丢失
- 重新上传数据集即可(几分钟)

### ⏱️ 冷启动
- 免费层**不会自动休眠**(比 Render 好!)
- 启动可能需要 30-60 秒

---

## 🔧 已创建的文件

| 文件 | 作用 |
|------|------|
| `railway.toml`(根) | 后端 Railway 配置 |
| `frontend/railway.toml` | 前端 Railway 配置 |

---

## 🆚 为什么不用 Render / Vercel / Netlify?

刚刚测试了主流平台:
- ❌ Render → 超时
- ❌ Vercel → 超时
- ❌ Netlify → 超时
- ❌ Cloudflare Pages → 超时
- ✅ **Railway → 可达!**

所以我们用 Railway 🚂
