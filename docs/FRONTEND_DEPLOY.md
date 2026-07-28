# 前端 Railway 部署 - Dockerfile 模式

## 关键配置

### Settings → Builder = Dockerfile
### Settings → Dockerfile Path = `frontend/Dockerfile`(相对 build context,不要带斜杠)

## 为什么不用 `/frontend/Dockerfile`

NIXPACKS Build with Dockerfile 模式:
- build context 默认是 git 根
- 路径 `/frontend/Dockerfile` 是绝对路径 → BuildKit 找根目录 `/frontend/Dockerfile`(不存在)
- 路径 `frontend/Dockerfile` 是相对路径 → BuildKit 找 `<root>/frontend/Dockerfile`(存在!)

## 配套 .gitignore

```toml
# railway.toml
[phases.setup]
nixPkgs = ["nodejs-20_x"]
```

## Dockerfile 关键点

- build context 是 git 根 → 用 `COPY frontend/package.json`
- 不要 `COPY . .`(会复制整个仓库)
- 显式 `COPY frontend/ ./` 在 builder 阶段
