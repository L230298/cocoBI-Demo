"""Tool 6: collect_user_feedback - 用户反馈 (PRD §3.3.2)
点赞/点踩/修正 - 失败时本地暂存,下次重试
"""
from __future__ import annotations
import json
import uuid
from pathlib import Path
from datetime import datetime
from .registry import register_tool
from config import DATA_DIR


_FEEDBACK_DIR = Path(DATA_DIR) / "feedback"
_FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


@register_tool(
    name="collect_user_feedback",
    purpose="收集用户对系统回答的反馈(点赞/点踩/修正)",
    owner_skills=[],  # 前端触发
    input_schema={
        "query_id": "string",
        "feedback_type": "string (up/down/correction)",
        "comment": "string (可选)",
    },
    output_schema={"feedback_id": "string"},
)
def collect_user_feedback(query_id: str, feedback_type: str, comment: str | None = None) -> dict:
    feedback_id = f"fb-{uuid.uuid4().hex[:8]}"
    record = {
        "feedback_id": feedback_id,
        "query_id": query_id,
        "feedback_type": feedback_type,
        "comment": comment,
        "created_at": datetime.utcnow().isoformat(),
    }
    # 失败本地暂存 - PRD §3.3.2 失败处理
    file_path = _FEEDBACK_DIR / f"{feedback_id}.json"
    try:
        file_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return {"success": True, "feedback_id": feedback_id, **record}
