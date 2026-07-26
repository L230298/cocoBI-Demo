"""Tool 1: execute_sql - SQL 执行 (PRD §3.3.2)
沙箱:SQLite 内存数据库,严格白名单 (只允许 SELECT + LIMIT)
"""
from __future__ import annotations
import sqlite3
import threading
from .registry import register_tool

# 每个 dataset_id 对应一个内存数据库,按需懒加载
_DB_CACHE: dict[str, sqlite3.Connection] = {}
_LOCK = threading.Lock()


def _get_or_load_db(dataset_id: str) -> sqlite3.Connection:
    """懒加载数据集到内存 SQLite - 文件一次性导入"""
    with _LOCK:
        if dataset_id in _DB_CACHE:
            return _DB_CACHE[dataset_id]

        from services.dataset_loader import load_dataset_to_sqlite

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        load_dataset_to_sqlite(conn, dataset_id)
        _DB_CACHE[dataset_id] = conn
        return conn


@register_tool(
    name="execute_sql",
    purpose="执行 NL2SQL Agent 生成的 SQL,返回数据",
    owner_skills=["nl2sql_agent"],
    input_schema={
        "sql": "string (必填,只能 SELECT,必带 LIMIT)",
        "dataset_id": "string (必填)",
        "params": "object (可选)",
    },
    output_schema={
        "success": "bool",
        "rows": "list[dict]",
        "row_count": "int",
        "elapsed_ms": "int",
    },
    forbidden_ops=["drop", "delete", "update", "insert", "truncate", "alter", "create", "replace"],
    timeout_seconds=5.0,
)
def execute_sql(sql: str, dataset_id: str, params: dict | None = None) -> dict:
    """同步执行 SQL,返回结果集"""
    import time

    if not sql or not dataset_id:
        return {"success": False, "error_code": "BadRequest", "error_msg": "sql 与 dataset_id 必填"}

    conn = _get_or_load_db(dataset_id)
    start = time.perf_counter()
    try:
        cursor = conn.execute(sql, params or {})
        rows = [dict(r) for r in cursor.fetchall()]
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "success": True,
            "rows": rows,
            "row_count": len(rows),
            "elapsed_ms": elapsed_ms,
        }
    except sqlite3.OperationalError as e:
        return {
            "success": False,
            "error_code": "SQLSyntaxError",
            "error_msg": str(e),
        }
    except Exception as e:
        return {"success": False, "error_code": type(e).__name__, "error_msg": str(e)}
