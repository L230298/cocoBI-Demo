"""反馈 API + 工具列表 API"""
from __future__ import annotations
from fastapi import APIRouter

from tools import invoke_tool
from tools.registry import _REGISTRY
from models.schemas import FeedbackRequest
from routers.chat import router as _  # noqa: F401  # ensure tools imported

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback")
async def feedback(req: FeedbackRequest):
    result = await invoke_tool(
        "collect_user_feedback",
        query_id=req.query_id,
        feedback_type=req.feedback_type,
        comment=req.comment,
        tags=req.tags,
    )
    return result


@router.get("/tools")
async def list_tools():
    """列出所有可用工具 - 调试用"""
    return {"success": True, "data": _REGISTRY.list_tools()}
