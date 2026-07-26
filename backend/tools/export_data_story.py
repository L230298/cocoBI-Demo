"""Tool 4: export_data_story - 导出数据故事 (PRD §3.3.2)
生成 markdown 文本 + 短链 ID,失败降级为纯文本
"""
from __future__ import annotations
import secrets
from pathlib import Path
from .registry import register_tool
from config import EXPORT_DIR


@register_tool(
    name="export_data_story",
    purpose="将 Storytelling Agent 输出导出为可分享的数据故事(含 URL/纯文本)",
    owner_skills=["storytelling_agent"],
    input_schema={"story": "object (DataStory)"},
    output_schema={"share_url": "string", "expire_at": "string", "markdown": "string"},
)
def export_data_story(story: dict) -> dict:
    """失败降级:URL 生成失败 → 返回 markdown 文本供复制"""
    story_id = story.get("story_id") or f"story-{secrets.token_hex(4)}"
    markdown = _render_markdown(story)

    try:
        # 持久化到本地文件,前端可访问 /api/story/{id}
        export_path = Path(EXPORT_DIR) / f"{story_id}.md"
        export_path.write_text(markdown, encoding="utf-8")
        share_url = f"/api/story/{story_id}/preview"
    except Exception:
        # 失败降级:不写文件,只返回 markdown - PRD §3.3.2 失败处理
        share_url = ""

    return {
        "success": True,
        "share_url": share_url,
        "expire_at": "2099-12-31T23:59:59Z",
        "markdown": markdown,
        "story_id": story_id,
    }


def _render_markdown(story: dict) -> str:
    lines = [f"# {story.get('title', '数据故事')}", "", f"> {story.get('summary', '')}", ""]
    for sec in story.get("sections", []):
        lines.append(f"## {sec.get('title', '')}")
        lines.append(sec.get("description", ""))
        lines.append("")

    if story.get("observations"):
        lines.append("## 💡 可关注观察点")
        for obs in story["observations"]:
            lines.append(f"- {obs.get('text', '')}")
        lines.append("")

    if story.get("next_steps"):
        lines.append("## 🎯 下一步建议")
        for step in story["next_steps"]:
            lines.append(f"- {step.get('text', '')}")
        lines.append("")

    return "\n".join(lines)
