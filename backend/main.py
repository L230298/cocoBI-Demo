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
from services.analytics import ANALYTICS_DIR
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
    """下载日志 / 埋点数据

    支持的文件(file 参数):
    - 不传: app.log(当前正在写的应用日志)
    - app.log / app.log.N (N=1,2,3...): 应用日志 (含轮转历史)
    - events.jsonl: 埋点事件 (每行一个 JSON, 14 个字段)

    支持的格式(format 参数):
    - text (默认): 原始文本 / JSONL
    - csv: 转成 CSV (UTF-8 BOM, Excel 友好)

    since/until: ISO 8601 UTC 时间范围过滤
    - app.log: 按日志首行时间戳
    - events.jsonl: 按 events.time 字段
    """
    from fastapi.responses import FileResponse, Response
    from fastapi import HTTPException
    import re
    import csv
    import io
    from datetime import datetime, timezone
    from config import LOG_DIR

    # ---------- 1. 解析目标文件 ----------
    is_events = (file == "events.jsonl")
    if file is None or file == "app.log":
        log_file = LOG_DIR / "app.log"
        base_name = "cocoBI-app"
        ext = "log"
    elif re.fullmatch(r"app\.log(\.\d+)?", file):
        log_file = LOG_DIR / file
        base_name = "cocoBI-app"
        ext = "log"
    elif is_events:
        log_file = ANALYTICS_DIR / "events.jsonl"
        base_name = "cocoBI-events"
        ext = "jsonl"
    else:
        raise HTTPException(status_code=400, detail=f"非法的文件名: {file} (允许: app.log / app.log.N / events.jsonl)")

    if not log_file.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在: {file or 'app.log'}")

    # ---------- 2. 解析时间范围 ----------
    def _parse_iso_utc(s: str | None) -> datetime | None:
        if not s:
            return None
        try:
            ss = s.strip()
            if ss.endswith("Z"):
                ss = ss[:-1] + "+00:00"
            dt = datetime.fromisoformat(ss)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.replace(tzinfo=None)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"时间格式错误 ({s}): {e}")

    since_dt = _parse_iso_utc(since)
    until_dt = _parse_iso_utc(until)
    if since_dt and until_dt and since_dt > until_dt:
        raise HTTPException(status_code=400, detail="since 必须早于 until")

    fmt = (format or "text").lower()
    if fmt not in ("text", "csv"):
        raise HTTPException(status_code=400, detail=f"不支持的 format: {fmt} (可选: text / csv)")

    # 文件名后缀带范围提示
    range_tag = ""
    if since_dt or until_dt:
        bits = []
        if since_dt:
            bits.append("from-" + since_dt.strftime("%Y%m%dT%H%M%SZ"))
        if until_dt:
            bits.append("to-" + until_dt.strftime("%Y%m%dT%H%M%SZ"))
        range_tag = "-" + "_".join(bits)
    display_name = f"{base_name}-{datetime.utcnow().strftime('%Y%m%d')}{range_tag}.{ext}"

    try:
        raw_text = log_file.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {e}")

    # ---------- 3a. events.jsonl 分支 ----------
    if is_events:
        return _build_events_response(raw_text, fmt, since_dt, until_dt, display_name)

    # ---------- 3b. app.log 分支(原逻辑) ----------
    line_re = re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})"
        r" \[(?P<level>\w+)\] (?P<logger>[^:]+): (?P<msg>.*)$"
    )

    def _parse_ts(ts_str: str) -> datetime | None:
        try:
            return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S,%f")
        except Exception:
            return None

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

    if fmt == "text":
        body = "\n".join(line for _, lines in filtered for _, line in lines)
        if body:
            body += "\n"
        # ext 已是 .log, 直接用 display_name
        return Response(
            content=body,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{display_name}"'},
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

    csv_name = display_name.rsplit(".", 1)[0] + ".csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{csv_name}"'},
    )


def _build_events_response(
    raw_text: str,
    fmt: str,
    since_dt,
    until_dt,
    display_name: str,
):
    """构建 events.jsonl 的下载响应

    - text: 原样返回 (JSONL)
    - csv: 把每行 JSON 拍平成表格, 列固定 14 个字段
    - since/until: 按 events.time 字段过滤
    """
    from fastapi.responses import Response
    from datetime import datetime, timezone
    import csv
    import io

    # events.jsonl 的 14 个标准字段 (analytics.py 中 record_event 的字段顺序)
    EVENT_COLS = [
        "time", "run_id", "event_type", "page_version",
        "session_id", "query_id", "user_input",
        "intent_recognized", "intent_confidence", "slots",
        "schema_mapped", "sql_generated", "sql_confidence",
        "sql_retry_count", "sql_executed_status", "sql_elapsed_ms",
        "row_count", "story_generated", "next_steps_count",
        "followups_count", "error_code", "error_stage",
        "error_msg", "extra",
    ]

    def _parse_event_ts(time_str: str):
        """解析 events.time (ISO 8601 带时区) -> naive UTC"""
        try:
            ss = time_str.strip()
            if ss.endswith("Z"):
                ss = ss[:-1] + "+00:00"
            dt = datetime.fromisoformat(ss)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            return None

    # 解析 + 过滤
    parsed = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = __import__("json").loads(line)
        except Exception:
            continue
        ts = _parse_event_ts(obj.get("time", ""))
        if since_dt and (ts is None or ts < since_dt):
            continue
        if until_dt and (ts is None or ts > until_dt):
            continue
        parsed.append(obj)

    if fmt == "text":
        json_mod = __import__("json")
        body = "\n".join(json_mod.dumps(o, ensure_ascii=False, default=str) for o in parsed)
        if body:
            body += "\n"
        return Response(
            content=body,
            media_type="application/x-ndjson; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{display_name}"'},
        )

    # CSV: 固定 24 列表头, 缺失字段填空
    buf = io.StringIO()
    buf.write("﻿")
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
    writer.writerow(EVENT_COLS)
    for obj in parsed:
        writer.writerow([obj.get(c, "") for c in EVENT_COLS])

    csv_name = display_name.rsplit(".", 1)[0] + ".csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{csv_name}"'},
    )


@app.get("/api/log/list")
async def list_logs():
    """列出所有日志文件 (含轮转的 + 埋点 events.jsonl)"""
    from config import LOG_DIR
    files = []
    # 应用日志 (含轮转)
    for f in LOG_DIR.glob("app.log*"):
        stat = f.stat()
        files.append({
            "name": f.name,
            "size_bytes": stat.st_size,
            "modified": __import__("datetime").datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "category": "log",
        })
    # 埋点 events.jsonl (单独目录)
    events_file = ANALYTICS_DIR / "events.jsonl"
    if events_file.exists():
        stat = events_file.stat()
        files.append({
            "name": events_file.name,
            "size_bytes": stat.st_size,
            "modified": __import__("datetime").datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "category": "events",
        })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"log_dir": str(LOG_DIR), "analytics_dir": str(ANALYTICS_DIR), "files": files}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
