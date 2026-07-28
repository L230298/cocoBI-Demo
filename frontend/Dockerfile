# cocoBI 前端 Dockerfile
# 完全控制 build,避免 NIXPACKS 缓存
FROM node:20-slim AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci || npm install

COPY . .
RUN npm run build

# ── runtime ──
FROM node:20-slim
WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/server.js ./
COPY --from=builder /app/package.json ./

RUN npm ci --omit=dev || npm install --omit=dev

ENV PORT=4173
ENV BACKEND_URL=https://cocobi-backend-production.up.railway.app

EXPOSE 4173
CMD ["node", "server.js"]
