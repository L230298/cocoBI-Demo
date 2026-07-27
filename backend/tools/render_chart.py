"""Tool 3: render_chart - 图表渲染 (PRD §3.3.2)
返回 ECharts 配置对象,前端直接渲染
"""
from __future__ import annotations
import re
from .registry import register_tool


# Y 轴单位映射 - 根据指标名自动添加单位
_Y_UNIT_MAP = {
    "销售额": "销售额（元）",
    "GMV": "销售额（元）",
    "营收": "销售额（元）",
    "金额": "金额（元）",
    "amount": "金额（元）",
    "profit": "利润（元）",
    "利润": "利润（元）",
    "用户数": "用户数（人）",
    "数量": "数量",
    "销量": "销量",
    "quantity": "数量",
}


def _infer_y_unit(y_field: str) -> str:
    """从 y_field 名推断 Y 轴单位"""
    if not y_field:
        return ""
    # 精确匹配
    if y_field in _Y_UNIT_MAP:
        return _Y_UNIT_MAP[y_field]
    # 子串匹配(中文优先)
    for key, unit in _Y_UNIT_MAP.items():
        if key in y_field:
            return unit
    return ""


def _detect_chart_type(data: list[dict]) -> str:
    """自动检测图表类型 - PRD §3.4.4 fallback"""
    if not data:
        return "table"
    first = data[0]
    keys = list(first.keys())
    # 时间序列 → line
    if any("date" in k.lower() or "time" in k.lower() or "日期" in k for k in keys):
        return "line"
    # 两个字段 (类目 + 数值) → bar
    if len(keys) == 2:
        return "bar"
    # 3 个及以上字段,带占比/份额 → pie
    if len(data) <= 8 and len(keys) == 2:
        return "pie"
    return "bar"


def _downsample(data: list[dict], max_points: int = 50) -> list[dict]:
    """降采样:超过 max_points 自动合并 Top-10 + 其他 - PRD §3.3.2 失败处理"""
    if len(data) <= max_points:
        return data
    numeric_key = None
    for k, v in data[0].items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            numeric_key = k
            break
    if not numeric_key:
        return data[:max_points]
    sorted_data = sorted(data, key=lambda r: r.get(numeric_key, 0), reverse=True)
    top = sorted_data[:10]
    other_sum = sum(r.get(numeric_key, 0) for r in sorted_data[10:])
    if other_sum:
        top.append({**{k: "其他" for k in sorted_data[0].keys()}, numeric_key: other_sum})
    return top


@register_tool(
    name="render_chart",
    purpose="根据数据类型生成最佳图表(ECharts 配置)",
    owner_skills=["storytelling_agent"],
    input_schema={
        "data": "list[dict] (必填)",
        "chart_type": "string (可选:bar/line/pie/funnel/table,缺省自动检测)",
        "title": "string",
    },
    output_schema={"chart_type": "string", "config": "object", "base64_thumbnail": "string (可选)"},
    timeout_seconds=3.0,
)
def render_chart(data: list[dict], chart_type: str = "auto", title: str = "") -> dict:
    if not data:
        return {
            "success": True,
            "chart_type": "table",
            "config": _empty_config(title or "暂无数据"),
        }

    if chart_type == "auto":
        chart_type = _detect_chart_type(data)

    if len(data) > 1000 and chart_type == "line":
        # 数据点过多 → 降级为聚合图 - PRD §3.3.2
        data = _downsample(data, max_points=200)

    keys = list(data[0].keys())
    x_field = keys[0]
    y_field = next((k for k in keys if isinstance(data[0][k], (int, float))), keys[1] if len(keys) > 1 else keys[0])
    series_field = keys[2] if len(keys) > 2 else None

    # Y 轴单位(自动添加)
    y_unit = _infer_y_unit(y_field)

    # 数据标签 - 自动显示在柱子上方
    label_config = {
        "show": True,
        "position": "top",
        "fontSize": 11,
        "color": "#333",
        "formatter": "{c}",
    } if chart_type in ("bar", "line") else None

    config = {
        "title": {
            "text": title or y_field,
            "left": "center",
            "textStyle": {"fontSize": 16, "fontWeight": "bold"},
        },
        "tooltip": {
            "trigger": "axis" if chart_type != "pie" else "item",
            "axisPointer": {"type": "shadow"} if chart_type == "bar" else None,
        },
        "grid": (
            {"left": "5%", "right": "5%", "bottom": "10%", "top": "15%", "containLabel": True}
            if chart_type != "pie"
            else {}
        ),
        "xAxis": (
            {
                "type": "category",
                "data": [str(r.get(x_field, "")) for r in data],
                "axisLabel": {"rotate": 0, "interval": 0},
            }
            if chart_type != "pie"
            else None
        ),
        "yAxis": (
            {
                "type": "value",
                "name": y_unit,
                "nameLocation": "end",
                "nameGap": 15,
                "nameTextStyle": {"fontSize": 12, "color": "#666"},
            }
            if chart_type != "pie"
            else None
        ),
        "series": [
            {
                "name": y_field,
                "type": "bar" if chart_type == "bar" else "line" if chart_type == "line" else "pie",
                "data": (
                    [r.get(y_field, 0) for r in data]
                    if chart_type != "pie"
                    else [
                        {"name": str(r.get(x_field, "")), "value": r.get(y_field, 0)}
                        for r in data
                    ]
                ),
                "label": label_config,
                "itemStyle": (
                    {
                        "color": (
                            "#5470c6"
                            if chart_type == "bar"
                            else "#91cc75" if chart_type == "line" else None
                        )
                    }
                    if chart_type in ("bar", "line")
                    else None
                ),
            }
        ],
    }
    return {"success": True, "chart_type": chart_type, "config": config}


def _empty_config(title: str) -> dict:
    return {
        "title": {"text": title, "left": "center", "subtext": "暂无数据"},
        "xAxis": {"type": "category", "data": []},
        "yAxis": {"type": "value"},
        "series": [],
    }
