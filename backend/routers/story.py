"""数据故事 API - 短链分享预览 + 反馈 + 工具列表"""
from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from config import EXPORT_DIR
from tools import get_tool
from tools.registry import _REGISTRY
from services.markdown_renderer import md_to_html
from routers.chat import router as _  # noqa: F401  # ensure tools imported

router = APIRouter(prefix="/api/story", tags=["story"])


@router.get("/{story_id}/preview")
async def preview(story_id: str):
    """短链分享预览页 - PRD §1.2 短链分享"""
    file_path = Path(EXPORT_DIR) / f"{story_id}.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="故事不存在")
    content = file_path.read_text(encoding="utf-8")
    html = md_to_html(content)
    return HTMLResponse(content=html)
