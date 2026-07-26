"""Tool 1: execute_sql - SQL 执行 (PRD §3.3.2)
沙箱:SQLite 磁盘数据库,严格白名单 (只允许 SELECT + LIMIT)

数据持久化:每个数据集一个 .db 文件,放在 /app/data/dbs/
需要 Railway Volume 挂载在 /app/data 让数据跨部署持久
"""
from __future__ import annotations
import sqlite3
import threading
from pathlib import Path
from .registry import register_tool

# 每个 dataset_id 对应一个磁盘 SQLite 数据库 - 在 Railway Volume 内
# /app/data/dbs/<dataset_id>.db
_DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path("./data")
DBS_DIR = _DATA_DIR / "dbs"
DBS_DIR.mkdir(parents=True, exist_ok=True)

_DB_CACHE: dict[str, sqlite3.Connection] = {}
_LOCK = threading.Lock()


def _get_or_load_db(dataset_id: str) -> sqlite3.Connection:
    """懒加载数据集到磁盘 SQLite - 文件持久"""
    with _LOCK:
        if dataset_id in _DB_CACHE:
            return _DB_CACHE[dataset_id]

        from services.dataset_loader import load_dataset_to_sqlite
        from config import UPLOAD_DIR, DATA_DIR

        # 1. 找上传文件路径(/app/data/uploads/<dataset_id>.csv|xlsx)
        upload_path = _find_upload_file(dataset_id)
        if not upload_path:
            return None

        # 2. SQLite 文件路径
        db_path = DBS_DIR / f"{dataset_id}.db"
        db_file = str(db_path)

        # 3. 连接(或新建)
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # 4. 加载数据到表
        try:
            load_dataset_to_sqlite(conn, dataset_id)
            conn.commit()
        except Exception as e:
            conn.close()
            raise

        _DB_CACHE[dataset_id] = conn
        return conn


def _find_upload_file(dataset_id: str) -> Path | None:
    """根据 dataset_registry 找到上传文件路径"""
    from services.dataset_registry import get_dataset

    ds = get_dataset(dataset_id)
    if not ds:
        return None

    # 优先从 file_path 字段
    file_path = ds.get("file_path") or ds.get("file")
    if file_path:
        p = Path(file_path)
        # 如果是容器内路径,尝试本地路径
        if p.exists():
            return p
        # /app/data/uploads/xxx.csv -> ./data/uploads/xxx.csv
        if str(p).startswith("/app/"):
            rel = str(p)[5:]  # strip /app/
            return Path("./backend") / rel
        return p

    # 备用: 用 upload dir 直接拼
    from config import UPLOAD_DIR
    for ext in [".csv", ".xlsx", ".xls"]:
        p = Path(UPLOAD_DIR) / f"{dataset_id}{ext}"
        if p.exists():
            return p
    return None


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
