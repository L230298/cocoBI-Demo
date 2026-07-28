# cocoBI 前端 Dockerfile
# build context = git 根,所以显式 cp frontend/*

# ===== build stage =====
FROM node:20-slim AS builder

WORKDIR /build
COPY frontend/package.json ./package.json
COPY frontend/package-lock.json* ./package-lock.json*
RUN npm install --no-audit --no-fund || npm install --no-audit --no-fund

# 复制所有 frontend 文件并 build
COPY frontend/ ./
RUN npm run build

# ===== runtime stage =====
FROM node:20-slim
WORKDIR /app
COPY --from=builder /build/dist ./dist
COPY frontend/server.js ./
COPY frontend/package.json ./

RUN npm install --omit=dev --no-audit --no-fund

ENV PORT=4173
ENV BACKEND_URL=https://cocobi-backend-production.up.railway.app

EXPOSE 4173
CMD ["node", "server.js"]
