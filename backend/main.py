"""cocoBI 后端入口 - FastAPI"""
from __future__ import annotations
import json
import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
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


# 422 校验错误:在被 Pydantic 拦下之前补一条埋点, 用于观测「空查询/超长查询」等被前端漏掉的情况
@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """RequestValidationError -> 422: 写一条 query_rejected 埋点, 然后返回标准 422"""
    try:
        from services.analytics import record_event

        body_bytes = b""
        try:
            body_bytes = await request.body()
        except Exception:
            pass
        user_input = ""
        session_id = ""
        dataset_id = ""
        try:
            payload = json.loads(body_bytes.decode("utf-8") or "{}")
            user_input = (payload.get("user_input") or "")[:500]
            session_id = (payload.get("session_id") or "")[:64]
            dataset_id = (payload.get("dataset_id") or "")[:64]
        except Exception:
            pass

        # 解析具体哪个字段出错(空字符串 -> min_length, 超长 -> max_length)
        err_list = []
        try:
            for e in exc.errors():
                loc = ".".join(str(x) for x in e.get("loc", []))
                err_list.append({"loc": loc, "type": e.get("type"), "msg": e.get("msg")})
        except Exception:
            pass

        try:
            record_event(
                event_type="query_rejected",
                user_input=user_input,
                session_id=session_id,
                error_code="ValidationError_422",
                error_stage="request_validation",
                error_msg=str(err_list)[:1000],
                extra={"dataset_id": dataset_id, "validation_errors": err_list, "url_path": str(request.url.path)},
            )
        except Exception as e:
            logger.warning(f"query_rejected 埋点失败: {e}")

        logger.info(f"422 ValidationError on {request.url.path}: {err_list}")
    except Exception as e:
        logger.warning(f"422 handler 异常: {e}")

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error_code": "ValidationError_422",
            "error_msg": "请求参数校验失败",
            "detail": err_list,
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
    since: str | None = None,
    until: str | None = None,
):
    """下载应用日志 - 支持下载当前日志或轮转历史日志

    - 不传 file: 下载 app.log(当前正在写的)
    - 传 file=app.log.1 / app.log.2 ... : 下载对应的轮转备份
    - format=text (默认): 原始文本
    - format=csv: 转成 CSV (UTF-8 BOM, Excel 友好) 列: line/timestamp/level/logger/message
    - since/until: 时间范围过滤 (ISO 8601, UTC), 例如 since=2026-08-03T00:00:00Z
      多行 traceback 跟首行同一记录, 整段保留或整段丢弃
    """
    from fastapi.responses import FileResponse, Response
    from fastapi import HTTPException
    import re
    import csv
    import io
    from datetime import datetime, timezone
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

    # 解析时间范围(支持带 Z 后缀的 UTC ISO 8601)
    def _parse_iso_utc(s: str | None) -> datetime | None:
        if not s:
            return None
        try:
            # 允许 "...Z" 或 "+00:00" 或 naive(默认 UTC)
            ss = s.strip()
            if ss.endswith("Z"):
                ss = ss[:-1] + "+00:00"
            dt = datetime.fromisoformat(ss)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.replace(tzinfo=None)  # 后续与 naive UTC 时间戳比较
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"时间格式错误 ({s}): {e}")

    since_dt = _parse_iso_utc(since)
    until_dt = _parse_iso_utc(until)
    if since_dt and until_dt and since_dt > until_dt:
        raise HTTPException(status_code=400, detail="since 必须早于 until")

    fmt = (format or "text").lower()
    if fmt not in ("text", "csv"):
        raise HTTPException(status_code=400, detail=f"不支持的 format: {fmt} (可选: text / csv)")

    # 解析日志行(首行带时间戳,后续多行为 traceback)
    line_re = re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})"
        r" \[(?P<level>\w+)\] (?P<logger>[^:]+): (?P<msg>.*)$"
    )

    def _parse_ts(ts_str: str) -> datetime | None:
        try:
            return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S,%f")
        except Exception:
            return None

    try:
        raw_text = log_file.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {e}")

    # 把日志切成 records(一条 = 第一行带 ts + 后续到下一个 ts 为止的多行)
    records: list[tuple[datetime | None, list[tuple[int, str]]]] = []
    current_ts: datetime | None = None
    current_lines: list[tuple[int, str]] = []
    for idx, line in enumerate(raw_text.splitlines(), start=1):
        m = line_re.match(line)
        if m:
            if current_lines:
                records.append((current_ts, current_lines))
            current_ts = _parse_ts(m["ts"])
            current_lines = [(idx, line)]
        else:
            current_lines.append((idx, line))
    if current_lines:
        records.append((current_ts, current_lines))

    # 按时间戳过滤: 无法解析时间戳的行(空记录开头之前的)始终保留;其他按范围
    def _in_range(ts: datetime | None) -> bool:
        if ts is None:
            return True  # 兜底保留
        if since_dt and ts < since_dt:
            return False
        if until_dt and ts > until_dt:
            return False
        return True

    filtered = [(ts, lines) for ts, lines in records if _in_range(ts)]

    # 输出文件名后缀带上过滤提示(可选)
    range_tag = ""
    if since_dt or until_dt:
        bits = []
        if since_dt:
            bits.append("from-" + since_dt.strftime("%Y%m%dT%H%M%SZ"))
        if until_dt:
            bits.append("to-" + until_dt.strftime("%Y%m%dT%H%M%SZ"))
        range_tag = "-" + "_".join(bits)

    if fmt == "text":
        body = "\n".join(line for _, lines in filtered for _, line in lines)
        if body:
            body += "\n"
        text_name = display_name.rsplit(".", 1)[0] + range_tag + ".log"
        return Response(
            content=body,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{text_name}"'},
        )

    # CSV
    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM, Excel 友好
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
    writer.writerow(["line", "timestamp", "level", "logger", "message"])
    for ts, lines in filtered:
        first_idx, first_line = lines[0]
        m = line_re.match(first_line)
        if m and ts is not None:
            ts_iso = m["ts"].replace(",", ".").replace(" ", "T") + "Z"
            level = m["level"]
            logger = m["logger"].strip()
            # 多行 traceback 的后续行拼到 message,行号保留首行
            if len(lines) > 1:
                msg = m["msg"] + "\n" + "\n".join(l for _, l in lines[1:])
            else:
                msg = m["msg"]
            writer.writerow([first_idx, ts_iso, level, logger, msg])
        else:
            # 整段无法解析(几乎不会出现)
            msg = "\n".join(l for _, l in lines)
            writer.writerow([first_idx, "", "RAW", "", msg])

    csv_name = display_name.rsplit(".", 1)[0] + range_tag + ".csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{csv_name}"'},
    )


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
