"""埋点模块 - PRD §3.6.2 事件埋点
按 14 个字段记录用户查询链路的关键事件,保存到本地 JSONL 文件。
"""
from __future__ import annotations
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import DATA_DIR

# 埋点文件路径: backend/data/analytics/events.jsonl
ANALYTICS_DIR = DATA_DIR / "analytics"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_FILE = ANALYTICS_DIR / "events.jsonl"

# 当前运行标识 (用于区分多次评测)
_RUN_ID = os.environ.get("EVAL_RUN_ID") or datetime.now().strftime("%Y%m%d-%H%M%S")
_PAGE_VERSION = os.environ.get("EVAL_PAGE_VERSION", "1.0.1-eval")

_LOCK = threading.Lock()


def _ensure_file() -> None:
    """确保文件存在,如果不存在则创建并写入表头"""
    if not EVENTS_FILE.exists():
        EVENTS_FILE.touch()


def _truncate(value: Any, limit: int = 4000) -> Any:
    """防止超大字段把日志撑爆"""
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f"...(截断,原长{len(value)})"
    return value


def record_event(
    *,
    event_type: str,
    user_input: str = "",
    session_id: str = "",
    query_id: str = "",
    intent_recognized: str = "",
    intent_confidence: float | None = None,
    slots: dict | None = None,
    schema_mapped: dict | None = None,
    sql_generated: str = "",
    sql_confidence: float | None = None,
    sql_retry_count: int = 0,
    sql_executed_status: str = "",
    sql_elapsed_ms: int | None = None,
    row_count: int | None = None,
    story_generated: dict | None = None,
    next_steps_count: int | None = None,
    followups_count: int | None = None,
    error_code: str = "",
    error_stage: str = "",
    error_msg: str = "",
    extra: dict | None = None,
) -> dict:
    """记录一条埋点事件

    event_type 必须是 PRD §3.6.2 规定的 11 个事件之一:
    - query_submitted / intent_recognized / sql_generated / sql_executed
    - story_generated / story_shared / story_exported / feedback_submitted
    - task_cancelled / dataset_uploaded / error_occurred
    """
    event = {
        "time": datetime.now(timezone.utc).isoformat(),
        "run_id": _RUN_ID,
        "event_type": event_type,
        "page_version": _PAGE_VERSION,
        "session_id": session_id,
        "query_id": query_id or (uuid.uuid4().hex[:8] if event_type != "query_submitted" else ""),
        "user_input": _truncate(user_input, 500),
        "intent_recognized": intent_recognized,
        "intent_confidence": intent_confidence,
        "slots": _truncate(json.dumps(slots, ensure_ascii=False), 1500) if slots else "",
        "schema_mapped": _truncate(json.dumps(schema_mapped, ensure_ascii=False), 2000) if schema_mapped else "",
        "sql_generated": _truncate(sql_generated, 2000),
        "sql_confidence": sql_confidence,
        "sql_retry_count": sql_retry_count,
        "sql_executed_status": sql_executed_status,
        "sql_elapsed_ms": sql_elapsed_ms,
        "row_count": row_count,
        "story_generated": _truncate(json.dumps(story_generated, ensure_ascii=False), 3000) if story_generated else "",
        "next_steps_count": next_steps_count,
        "followups_count": followups_count,
        "error_code": error_code,
        "error_stage": error_stage,
        "error_msg": _truncate(error_msg, 1000),
        "extra": _truncate(json.dumps(extra, ensure_ascii=False), 1000) if extra else "",
    }

    with _LOCK:
        _ensure_file()
        with EVENTS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    return event


def get_events_path() -> Path:
    """返回埋点文件路径,供前端/外部访问"""
    return EVENTS_FILE


def reset_events() -> None:
    """清空埋点文件,新一轮评测前调用"""
    with _LOCK:
        if EVENTS_FILE.exists():
            EVENTS_FILE.unlink()
        _ensure_file()


def count_events() -> int:
    """统计埋点行数"""
    if not EVENTS_FILE.exists():
        return 0
    with _LOCK:
        n = 0
        with EVENTS_FILE.open("r", encoding="utf-8") as f:
            for _ in f:
                n += 1
        return n


def list_events(limit: int | None = None) -> list[dict]:
    """读取最近 N 条事件"""
    if not EVENTS_FILE.exists():
        return []
    with _LOCK:
        events: list[dict] = []
        with EVENTS_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    if limit:
        events = events[-limit:]
    return events