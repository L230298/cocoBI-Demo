"""数据故事 API - 短链分享预览 + 反馈 + 工具列表"""
from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from config import EXPORT_DIR
from tools import get_tool
from tools.registry import _REGISTRY
from routers.chat import router as _  # noqa: F401  # ensure tools imported

router = APIRouter(prefix="/api/story", tags=["story"])


@router.get("/{story_id}/preview")
async def preview(story_id: str):
    """短链分享预览页 - PRD §1.2 短链分享"""
    file_path = Path(EXPORT_DIR) / f"{story_id}.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="故事不存在")
    content = file_path.read_text(encoding="utf-8")
    # 渲染为简易 HTML
    html = _md_to_html(content)
    return HTMLResponse(content=html)


def _md_to_html(md: str) -> str:
    """极简 Markdown 渲染"""
    lines = md.split("\n")
    html_lines = ['<html><head><meta charset="utf-8"><title>cocoBI 故事</title>',
                  '<style>body{font-family:-apple-system,sans-serif;max-width:780px;margin:40px auto;padding:0 20px;line-height:1.7;color:#222}h1{color:#5b6cff}h2{margin-top:32px;color:#333;border-bottom:1px solid #eee;padding-bottom:8px}li{margin:8px 0}</style></head><body>']
    in_list = False
    for line in lines:
        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{line[2:]}</li>")
        else:
            if in_list and not line.strip():
                html_lines.append("</ul>")
                in_list = False
            if line.strip():
                html_lines.append(f"<p>{line}</p>")
    if in_list:
        html_lines.append("</ul>")
    html_lines.append("</body></html>")
    return "\n".join(html_lines)
