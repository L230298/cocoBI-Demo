"""共享 Markdown → HTML 渲染器
供 story.py (分享页) 和 report.py (报告预览) 复用
"""
from __future__ import annotations
import re

_STYLE = """
<style>
  body{font-family:-apple-system,'Microsoft YaHei',sans-serif;max-width:880px;margin:40px auto;padding:0 24px;line-height:1.75;color:#222;background:#fafafa}
  .container{background:#fff;padding:32px 40px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
  h1{color:#1f3a68;font-size:1.8em;margin:0 0 16px;border-bottom:3px solid #5b6cff;padding-bottom:12px}
  h2{color:#333;margin-top:36px;font-size:1.25em;border-bottom:1px solid #eee;padding-bottom:6px}
  h3{color:#555;margin-top:24px;font-size:1.1em}
  blockquote{border-left:4px solid #5b6cff;background:#f0f4ff;margin:16px 0;padding:12px 16px;color:#333;border-radius:0 6px 6px 0}
  code{background:#f5f5f5;padding:2px 6px;border-radius:3px;font-family:Consolas,monospace;font-size:.9em;color:#003366}
  pre{background:#1e1e1e;color:#d4d4d4;padding:16px 20px;border-radius:6px;overflow-x:auto;line-height:1.5}
  pre code{background:transparent;color:inherit;padding:0;font-size:.85em}
  table{border-collapse:collapse;width:100%;margin:16px 0;font-size:.92em}
  th,td{border:1px solid #ddd;padding:8px 12px;text-align:left}
  th{background:#f5f7ff;font-weight:600;color:#1f3a68}
  tr:nth-child(even){background:#fafbff}
  ul{margin:12px 0;padding-left:24px}
  li{margin:6px 0}
  strong{color:#1f3a68}
  hr{border:none;border-top:1px dashed #ddd;margin:32px 0}
  .meta{color:#666;font-size:.9em;margin:8px 0}
  .footer{text-align:center;color:#999;font-size:.85em;margin-top:32px;padding-top:16px;border-top:1px solid #eee}
  .chart{width:100%;height:360px;margin:16px 0}
</style>
"""


def md_to_html(md: str, *, include_style: bool = True, full_document: bool = True) -> str:
    """把 markdown 渲染成 HTML

    include_style: 是否包含 <style> (内嵌到现有页面时设为 False)
    full_document: 是否包 <html><body> 完整文档
    """
    lines = md.split("\n")
    out: list[str] = []

    if full_document:
        out.append(
            f'<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>cocoBI 报告</title>{_STYLE if include_style else ""}'
            f'</head><body><div class="container">'
        )

    in_code = False
    code_buf: list[str] = []
    code_lang = ""
    in_list = False
    chart_index = 0

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def render_inline(text: str) -> str:
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        return text

    def render_table(table_lines):
        if not table_lines:
            return
        head = [c.strip() for c in table_lines[0].strip("|").split("|")]
        body = []
        for line in table_lines[2:]:
            row = [c.strip() for c in line.strip("|").split("|")]
            body.append(row)
        out.append("<table>")
        out.append("<thead><tr>" + "".join(f"<th>{render_inline(h)}</th>" for h in head) + "</tr></thead>")
        out.append("<tbody>")
        for row in body:
            out.append("<tr>" + "".join(f"<td>{render_inline(c)}</td>" for c in row) + "</tr>")
        out.append("</tbody></table>")

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            if not in_code:
                close_list()
                in_code = True
                code_lang = line[3:].strip()
                code_buf = []
            else:
                if code_lang == "chart":
                    cid = f"chart-{chart_index}"
                    chart_index += 1
                    out.append(f'<div id="{cid}" class="chart"></div>')
                    out.append(
                        f'<script>if(window.echarts){{echarts.init(document.getElementById("{cid}")).setOption({chr(10).join(code_buf)});}}'
                        f'else{{document.getElementById("{cid}").innerText="图表加载中...";}}</script>'
                    )
                else:
                    out.append(f'<pre><code class="language-{code_lang}">{chr(10).join(code_buf)}</code></pre>')
                in_code = False
                code_buf = []
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if line.startswith("## "):
            close_list()
            out.append(f"<h2>{render_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            close_list()
            out.append(f"<h1>{render_inline(line[2:])}</h1>")
        elif line.startswith("### "):
            close_list()
            out.append(f"<h3>{render_inline(line[4:])}</h3>")
        elif line.strip() == "---":
            close_list()
            out.append("<hr>")
        elif line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip()):
            close_list()
            tbl = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            render_table(tbl)
            continue
        elif line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{render_inline(line[2:])}</li>")
        elif line.startswith("> "):
            close_list()
            out.append(f"<blockquote>{render_inline(line[2:])}</blockquote>")
        elif line.startswith("**") and line.endswith("**"):
            close_list()
            out.append(f'<p class="meta">{render_inline(line)}</p>')
        elif not line.strip():
            close_list()
        else:
            close_list()
            out.append(f"<p>{render_inline(line)}</p>")
        i += 1

    close_list()
    if full_document:
        # echarts CDN (只在完整文档时引入)
        if any('id="chart-' in x for x in out):
            out.append('<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>')
        out.append('<p class="footer">— 本报告由 cocoBI 自动生成 —</p>')
        out.append("</div></body></html>")

    return "\n".join(out)
