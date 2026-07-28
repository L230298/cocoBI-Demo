# cocoBI 前端 Dockerfile
# build context = frontend/ 本身(Railway Root Directory = frontend)
# 简化路径,避免 docker COPY 的 frontend/frontend/... 嵌套问题

# ===== build =====
FROM node:20-slim AS builder
WORKDIR /build
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY . .
RUN npm run build

# ===== runtime =====
FROM node:20-slim
WORKDIR /app
COPY --from=builder /build/dist ./dist
COPY server.js ./
COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

ENV PORT=4173
ENV BACKEND_URL=https://cocobi-backend-production.up.railway.app
EXPOSE 4173
CMD ["node", "server.js"]
