# cocoBI 后端 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖(利用 Docker 层缓存)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码 + 启动脚本
COPY . .
RUN chmod +x ./start.sh

# Railway 端口 - 默认 8080
EXPOSE 8080

# ENTRYPOINT 形式启动,变量替换最可靠
ENTRYPOINT ["./start.sh"]

# Rebuild trigger at Mon Jul 27 01:45:15     2026
# rebuild 1785123752
# rebuild 1785124628
# gmv-doc 1785125039
# multichat 1785133509
# intent-fix 1785134757
# intent-fix2 1785135152
# q19-fix 1785135302
# ta-fix 1785135381
# q5-fix 1785136589
# q4-q5 1785137137
# q4-metric-fix2 1785144352
# nameerror-fix 1785145319
# nameerror2 1785145559
# user-input-pipe 1785145939
