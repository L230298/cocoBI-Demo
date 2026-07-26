"""Session 管理 - 保存最近查询"""
from __future__ import annotations
import threading
from collections import defaultdict
from datetime import datetime

_LOCK = threading.Lock()
_QUERIES: dict[str, list[dict]] = defaultdict(list)  # user_id -> queries


def record_query(user_id: str, query: str, intent: str, slots: dict) -> None:
    with _LOCK:
        _QUERIES[user_id].insert(
            0,
            {
                "query": query,
                "intent": intent,
                "timestamp": datetime.utcnow().isoformat(),
                "slots": slots,
            },
        )
        # 最多保留 50 条
        _QUERIES[user_id] = _QUERIES[user_id][:50]


def get_recent_queries(user_id: str = "default", limit: int = 5) -> list[dict]:
    with _LOCK:
        return list(_QUERIES.get(user_id, []))[:limit]
