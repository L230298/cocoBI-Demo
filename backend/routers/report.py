"""数据分析报告生成 + SQL 编辑/重执行"""
from __future__ import annotations
import re
from io import BytesIO
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from tools import invoke_tool
from tools.execute_sql import _DB_CACHE, _get_or_load_db

router = APIRouter(prefix="/api", tags=["report"])

# SQL 白名单(防止破坏性操作)
_FORBIDDEN = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|TRUNCATE|ALTER|CREATE|REPLACE)\b",
    re.IGNORECASE,
)


def _build_docx(report: dict) -> bytes:
    """把 report dict 渲染成 .docx (Word) 文档, 返回字节"""
    from docx import Document
    from docx.shared import Pt, RGBColor

    doc = Document()

    # 标题
    title = doc.add_heading(report.get("title", "数据分析报告"), level=0)
    title.alignment = 1  # center

    # 元信息
    meta = doc.add_paragraph()
    meta_run = meta.add_run(
        f"数据集: {report.get('dataset_id', '-')}    "
        f"生成时间: {report.get('generated_at', '-')}"
    )
    meta_run.font.size = Pt(9)
    meta_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    # 每个 section
    for i, sec in enumerate(report.get("sections", []), 1):
        doc.add_heading(f"{i}. {sec.get('query', 'N/A')}", level=1)

        info = doc.add_paragraph()
        info_run = info.add_run(
            f"Intent: {sec.get('intent', '-')}   |   Rows: {sec.get('row_count', 0)}"
        )
        info_run.font.size = Pt(10)
        info_run.italic = True

        if sec.get("error"):
            err_p = doc.add_paragraph()
            err_run = err_p.add_run(f"❌ Error: {sec['error']}")
            err_run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
            continue

        # SQL 代码块
        doc.add_paragraph().add_run("SQL:").bold = True
        sql_p = doc.add_paragraph()
        sql_run = sql_p.add_run(sec.get("sql", "-") or "-")
        sql_run.font.name = "Consolas"
        sql_run.font.size = Pt(9)
        sql_run.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

        # 数据表
        cols = sec.get("columns", [])
        rows = sec.get("rows", [])
        if cols and rows:
            doc.add_paragraph().add_run("查询结果:").bold = True
            table = doc.add_table(rows=1, cols=len(cols))
            table.style = "Light Grid Accent 1"
            hdr = table.rows[0].cells
            for j, col in enumerate(cols):
                hdr[j].text = str(col)
                for run in hdr[j].paragraphs[0].runs:
                    run.bold = True
            for row in rows[:50]:
                cells = table.add_row().cells
                for j, col in enumerate(cols):
                    cells[j].text = str(row.get(col, ""))

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


class SqlEditRequest(BaseModel):
    """用户编辑 SQL 后重新执行"""
    sql: str
    dataset_id: str


class SqlEditResponse(BaseModel):
    """SQL 重执行结果"""
    success: bool
    columns: List[str] = []
    rows: List[dict] = []
    row_count: int = 0
    elapsed_ms: int = 0
    error: Optional[str] = None
    is_readonly: bool = True


@router.post("/sql/edit", response_model=SqlEditResponse)
async def edit_and_execute_sql(req: SqlEditRequest):
    """用户编辑 SQL 后重新执行(只允许 SELECT)"""
    sql = (req.sql or "").strip()
    if not sql:
        return SqlEditResponse(success=False, error="SQL 不能为空")

    if _FORBIDDEN.search(sql):
        return SqlEditResponse(
            success=False,
            is_readonly=False,
            error="SQL 包含禁止操作(DROP/DELETE/UPDATE/INSERT 等),只允许 SELECT",
        )

    if not sql.upper().startswith("SELECT"):
        return SqlEditResponse(
            success=False,
            is_readonly=False,
            error="只允许 SELECT 查询",
        )

    if "LIMIT" not in sql.upper():
        sql = sql.rstrip(";") + " LIMIT 1000"

    try:
        import time

        t0 = time.perf_counter()
        conn = _get_or_load_db(req.dataset_id)
        if conn is None:
            return SqlEditResponse(success=False, error="数据集未找到")
        cursor = conn.execute(sql)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        elapsed = int((time.perf_counter() - t0) * 1000)
        return SqlEditResponse(
            success=True,
            columns=cols,
            rows=rows,
            row_count=len(rows),
            elapsed_ms=elapsed,
        )
    except Exception as e:
        return SqlEditResponse(success=False, error=str(e))


class ReportGenerateRequest(BaseModel):
    """批量生成报告 - 接收选中的 query_ids"""
    query_ids: List[str]
    dataset_id: str
    title: Optional[str] = None
    format: str = "json"  # json | markdown | docx


@router.post("/report/generate")
async def generate_report(req: ReportGenerateRequest):
    """基于选中的 query_ids 生成数据报告

    每个 query_id 对应一个历史查询,会重新执行 SQL 拿数据
    format: json (默认) | markdown | docx
    """
    if not req.query_ids:
        raise HTTPException(status_code=400, detail="query_ids 不能为空")
    if req.format not in ("json", "markdown", "docx"):
        raise HTTPException(status_code=400, detail=f"不支持的 format: {req.format}")

    from services.session_service import get_recent_queries
    from services.dataset_registry import get_dataset

    # 从历史拿 query
    all_queries = get_recent_queries(limit=200)  # user_id="default" 默认
    selected = [q for q in all_queries if q.get("id") in req.query_ids]

    if not selected:
        # 可能是 reset 过,用 dataset_id 重新生成所有 query 的内容
        ds = get_dataset(req.dataset_id)
        if not ds:
            raise HTTPException(status_code=404, detail="数据集未找到")

    # 重新执行每个 query 的 SQL
    sections = []
    for q in selected:
        sql = q.get("sql") or ""
        if not sql:
            continue
        try:
            conn = _get_or_load_db(req.dataset_id)
            if not conn:
                continue
            cursor = conn.execute(sql)
            cols = [d[0] for d in cursor.description] if cursor.description else []
            rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
            sections.append({
                "query_id": q.get("id"),
                "query": q.get("query"),
                "intent": q.get("intent"),
                "sql": sql,
                "columns": cols,
                "rows": rows[:100],
                "row_count": len(rows),
                "timestamp": q.get("timestamp"),
            })
        except Exception as e:
            sections.append({
                "query_id": q.get("id"),
                "query": q.get("query"),
                "error": str(e),
            })

    report = {
        "title": req.title or f"数据分析报告 ({len(sections)} 个指标)",
        "dataset_id": req.dataset_id,
        "sections": sections,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
        "format": req.format,
    }

    if req.format == "markdown":
        md = f"# {report['title']}\n\n"
        for i, sec in enumerate(sections, 1):
            md += f"## {i}. {sec.get('query', 'N/A')}\n\n"
            md += f"**Intent**: {sec.get('intent', '-')}  |  **Rows**: {sec.get('row_count', 0)}\n\n"
            if sec.get("error"):
                md += f"> ❌ Error: {sec['error']}\n\n"
            else:
                md += f"```sql\n{sec.get('sql', '-')}\n```\n\n"
                if sec.get("rows"):
                    cols = sec["columns"]
                    md += "| " + " | ".join(cols) + " |\n"
                    md += "|" + "|".join(["---"] * len(cols)) + "|\n"
                    for row in sec["rows"][:20]:
                        md += "| " + " | ".join(str(row.get(c, "")) for c in cols) + " |\n"
                    md += "\n"
        report["markdown"] = md

    if req.format == "docx":
        # 返回 docx 二进制
        docx_bytes = _build_docx(report)
        # HTTP header 只能用 latin-1, 中文文件名要按 RFC 5987 转码
        from urllib.parse import quote
        raw_filename = f"数据分析报告-{report.get('generated_at', '')[:10]}.docx"
        encoded_filename = quote(raw_filename)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": (
                    f"attachment; "
                    f'filename="report.docx"; '  # ASCII fallback
                    f"filename*=UTF-8''{encoded_filename}"  # RFC 5987
                ),
                "Content-Length": str(len(docx_bytes)),
            },
        )

    return report
