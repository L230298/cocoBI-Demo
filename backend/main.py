"""cocoBI 后端入口 - FastAPI"""
from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import HOST, PORT, CORS_ORIGINS, SAMPLES_DIR, LOG_DIR
from routers import chat, dataset, story, feedback, report, user

# 导入所有工具以触发注册 - PRD §3.3.1
import tools  # noqa: F401
from tools import execute_sql  # noqa: F401
from tools import get_data_source_metadata  # noqa: F401
from tools import render_chart  # noqa: F401
from tools import export_data_story  # noqa: F401
from tools import get_recent_queries  # noqa: F401
from tools import collect_user_feedback  # noqa: F401
from tools import generate_next_steps  # noqa: F401

# 日志: 控制台 + 文件 (按大小轮转, 保留最近 5 个 × 5MB)
_file_handler = RotatingFileHandler(
    LOG_DIR / "app.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), _file_handler],
)
logger = logging.getLogger(__name__)
logger.info(f"日志初始化: {LOG_DIR / 'app.log'}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时自动注册示例数据集 + 扫描已上传的数据集"""
    from services.dataset_loader import parse_uploaded_file, load_existing_uploads

    # 1. 加载示例数据
    sample = SAMPLES_DIR / "retail_20260720_gmv.csv"
    if sample.exists():
        try:
            info = parse_uploaded_file(
                sample,
                dataset_name="示例-零售 GMV",
                industry_template="零售",
            )
            logger.info(f"示例数据集已加载: {info['dataset_id']} ({info['row_count']} 行)")
        except Exception as e:
            logger.warning(f"示例数据集加载失败: {e}")

    # 2. 扫描 /app/data/uploads 里的所有已上传文件,稳定 ID 重建注册表
    #    Volume 挂载后,文件还在,只需重新注册到内存
    load_existing_uploads()

    yield


app = FastAPI(
    title="cocoBI Demo",
    description="AI 数据分析助手 - 4 Agent 协作 + 7 工具 + 轻量闭环",
    version="1.0.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理 - PRD §3.4.7
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": type(exc).__name__,
            "error_msg": "系统开小差了,请稍后再试",  # 友好提示,不暴露技术细节
        },
    )


app.include_router(chat.router)
app.include_router(dataset.router)
app.include_router(story.router)
app.include_router(feedback.router)
app.include_router(report.router)
app.include_router(user.router)


@app.get("/")
async def root():
    return {
        "name": "cocoBI Demo",
        "version": "1.0.1",
        "docs": "/docs",
        "agents": ["IntentAgent", "SchemaAgent", "NL2SQLAgent", "StorytellingAgent"],
        "tools_count": 7,
        "intents": [
            "QueryBasicMetrics",
            "QueryCompareAndTopN",
            "ThresholdAlert",
            "AttributeAnalysis",
            "SmartInterpretation",
        ],
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/log/download")
async def download_log(
    file: str | None = None,
    format: str | None = None,
):
    """下载应用日志 - 支持下载当前日志或轮转历史日志

    - 不传 file: 下载 app.log(当前正在写的)
    - 传 file=app.log.1 / app.log.2 ... : 下载对应的轮转备份
    - format=text (默认): 原始文本
    - format=csv: 转成 CSV (UTF-8 BOM, Excel 友好) 列: line/timestamp/level/logger/message
    """
    from fastapi.responses import FileResponse, Response
    from fastapi import HTTPException
    import re
    import csv
    import io
    from datetime import datetime
    from config import LOG_DIR

    if file is None:
        log_file = LOG_DIR / "app.log"
        display_name = f"cocoBI-app-{datetime.utcnow().strftime('%Y%m%d')}.log"
    else:
        # 安全检查: 只允许 app.log / app.log.N(N 是数字),防路径穿越
        if not re.fullmatch(r"app\.log(\.\d+)?", file):
            raise HTTPException(status_code=400, detail=f"非法的日志文件名: {file}")
        log_file = LOG_DIR / file
        display_name = f"cocoBI-{file}"

    if not log_file.exists():
        raise HTTPException(status_code=404, detail=f"日志文件不存在: {display_name}")

    fmt = (format or "text").lower()
    if fmt == "text":
        return FileResponse(
            path=str(log_file),
            media_type="text/plain",
            filename=display_name,
        )

    if fmt == "csv":
        # 解析每行: 2026-08-03 10:23:45,774 [INFO] logger.name: message...
        line_re = re.compile(
            r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})"
            r" \[(?P<level>\w+)\] (?P<logger>[^:]+): (?P<msg>.*)$"
        )
        try:
            raw_text = log_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取日志失败: {e}")

        # UTF-8 BOM 让 Excel 直接识别中文不乱码
        buf = io.StringIO()
        buf.write("﻿")
        writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
        writer.writerow(["line", "timestamp", "level", "logger", "message"])
        for idx, line in enumerate(raw_text.splitlines(), start=1):
            m = line_re.match(line)
            if m:
                # 转成 ISO 8601 方便排序/筛选
                ts_iso = m["ts"].replace(",", ".").replace(" ", "T") + "Z"
                writer.writerow([idx, ts_iso, m["level"], m["logger"].strip(), m["msg"]])
            else:
                # 无法解析的多行 traceback 后续行,放到 message 保留原貌
                writer.writerow([idx, "", "RAW", "", line])

        csv_name = display_name.rsplit(".", 1)[0] + ".csv"
        return Response(
            content=buf.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{csv_name}"',
            },
        )

    raise HTTPException(status_code=400, detail=f"不支持的 format: {fmt} (可选: text / csv)")


@app.get("/api/log/list")
async def list_logs():
    """列出所有日志文件 (含轮转的)"""
    from config import LOG_DIR
    files = []
    for f in LOG_DIR.glob("app.log*"):
        stat = f.stat()
        files.append({
            "name": f.name,
            "size_bytes": stat.st_size,
            "modified": __import__("datetime").datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"log_dir": str(LOG_DIR), "files": files}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
