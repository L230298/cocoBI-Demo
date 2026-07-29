"""Session 管理 - 保存最近查询"""
from __future__ import annotations
import threading
import uuid
from collections import defaultdict
from datetime import datetime

_LOCK = threading.Lock()
_QUERIES: dict[str, list[dict]] = defaultdict(list)  # user_id -> queries


def record_query(user_id: str, query: str, intent: str, slots: dict) -> str:
    """记录一条 query 到 history,返回该 query 的 ID(供前端报告功能用)"""
    qid = uuid.uuid4().hex[:8]
    with _LOCK:
        _QUERIES[user_id].insert(
            0,
            {
                "id": qid,
                "query": query,
                "intent": intent,
                "timestamp": datetime.utcnow().isoformat(),
                "slots": slots,
            },
        )
        # 最多保留 50 条
        _QUERIES[user_id] = _QUERIES[user_id][:50]
    return qid


def get_recent_queries(user_id: str = "default", limit: int = 5) -> list[dict]:
    with _LOCK:
        return list(_QUERIES.get(user_id, []))[:limit]


def update_query_sql(user_id: str, query_id: str, sql: str) -> None:
    """NL2SQL 生成 SQL 后, 回填到 history(报告功能靠这个重跑 SQL)"""
    with _LOCK:
        for q in _QUERIES.get(user_id, []):
            if q.get("id") == query_id:
                q["sql"] = sql
                return


def update_query_charts(user_id: str, query_id: str, charts: list) -> None:
    """Storytelling Agent 生成图表后, 回填到 history(报告功能靠这个渲染图表)"""
    with _LOCK:
        for q in _QUERIES.get(user_id, []):
            if q.get("id") == query_id:
                q["charts"] = charts
                return
