# cocoBI 前端 Dockerfile
# build context = git 根,所以显式 cp frontend 内容

# ===== build =====
FROM node:20-slim AS builder
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ===== runtime =====
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
