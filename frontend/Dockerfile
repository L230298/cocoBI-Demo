# cocoBI 前端 Dockerfile
# 显式 Node 模式 - 避免 NIXPACKS Python builder 误识别

# ===== build stage =====
FROM node:20-slim AS builder

WORKDIR /app

# 只装必要的工具
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# 装依赖
COPY package.json ./
RUN npm install --no-audit --no-fund

# 复制源码 + build
COPY . .
RUN npm run build

# ===== runtime stage =====
FROM node:20-slim

WORKDIR /app

# 只装运行时依赖(更小的镜像)
COPY --from=builder /app/package.json ./
RUN npm install --omit=dev --no-audit --no-fund

# 复制 build 产物 + server.js
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/server.js ./

# Railway 自动设置 PORT,默认 4173
ENV PORT=4173
ENV BACKEND_URL=https://cocobi-backend-production.up.railway.app

EXPOSE 4173
CMD ["node", "server.js"]
