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
    """把数据故事的完整内容渲染成 markdown,供分享预览页用"""
    lines = [f"# {story.get('title', '数据故事')}", ""]

    # 1. 摘要 + 数据来源
    summary = story.get("summary")
    if isinstance(summary, list):
        summary = " ".join(str(s) for s in summary)
    if summary:
        lines.append(f"> {summary}")
        lines.append("")

    user_input = story.get("user_input")
    if user_input:
        lines.append(f"**用户问题**: {user_input}")
    intent = story.get("intent")
    if intent:
        lines.append(f"**分析意图**: {intent}")
    lines.append("")

    # 2. SQL
    sql = story.get("sql")
    if sql:
        lines.append("## 🔧 SQL 查询")
        lines.append("```sql")
        lines.append(sql)
        lines.append("```")
        lines.append("")

    # 3. 数据明细
    sql_result = story.get("sql_result") or {}
    rows = sql_result.get("rows") or []
    cols = sql_result.get("columns") or []
    # execute_sql 不返回 columns, 从 rows[0] 推断
    if rows and not cols:
        cols = list(rows[0].keys()) if isinstance(rows[0], dict) else []
    if rows and cols:
        lines.append(f"## 📋 数据明细 ({len(rows)} 行)")
        lines.append("| " + " | ".join(str(c) for c in cols) + " |")
        lines.append("|" + "|".join(["---"] * len(cols)) + "|")
        for r in rows[:30]:
            cells = []
            for c in cols:
                v = r.get(c, "") if isinstance(r, dict) else ""
                cells.append(str(v))
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    # 4. 图表 - 把 echarts config 嵌进 markdown, HTML 渲染时用 echarts 画
    charts = story.get("charts") or []
    if charts:
        lines.append(f"## 📊 数据图表 ({len(charts)} 张)")
        for i, ch in enumerate(charts, 1):
            chart_type = ch.get("chart_type", "")
            config = ch.get("config") or {}
            title = config.get("title", {}).get("text", "") if isinstance(config.get("title"), dict) else ""
            lines.append(f"### 图表 {i}: {title} ({chart_type})")
            # 用特殊代码块标记, HTML 渲染器会识别
            import json as _json
            lines.append("```chart")
            lines.append(_json.dumps(config, ensure_ascii=False, default=str))
            lines.append("```")
        lines.append("")

    # 5. 可关注观察点
    observations = story.get("observations") or []
    if observations:
        lines.append("## 💡 可关注观察点")
        for obs in observations:
            text = obs.get("text", "") if isinstance(obs, dict) else str(obs)
            lines.append(f"- {text}")
        lines.append("")

    # 6. 下一步建议
    next_steps = story.get("next_steps") or []
    if next_steps:
        lines.append("## 🎯 下一步建议")
        for step in next_steps:
            text = step.get("text", "") if isinstance(step, dict) else str(step)
            lines.append(f"- {text}")
        lines.append("")

    # 7. 推荐追问
    followups = story.get("recommended_followups") or []
    if followups:
        lines.append("## 🔍 推荐追问")
        for f in followups:
            text = f.get("text", "") if isinstance(f, dict) else str(f)
            lines.append(f"- {text}")
        lines.append("")

    # 8. 页脚
    lines.append("---")
    lines.append("*本数据故事由 cocoBI AI 数据分析助手自动生成*")

    return "\n".join(lines)
