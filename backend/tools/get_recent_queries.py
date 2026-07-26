"""Tool 5: get_recent_queries - 历史查询 (PRD §3.3.2)
用于上下文理解和快捷操作 - 只返回本人历史
"""
from .registry import register_tool
from services.session_service import get_recent_queries as _get


@register_tool(
    name="get_recent_queries",
    purpose="获取用户最近查询历史,用于上下文理解和快捷操作",
    owner_skills=["intent_agent"],
    input_schema={"user_id": "string", "limit": "int (默认 5)"},
    output_schema={"queries": "list[{query, intent, timestamp, slots}]"},
)
def get_recent_queries(user_id: str = "default", limit: int = 5) -> dict:
    queries = _get(user_id=user_id, limit=limit)
    return {"success": True, "queries": queries}
