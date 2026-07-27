"""Agent 4: StorytellingAgent - 故事化输出 (PRD §3.2.2)
整合前三 Agent 输出,生成可分享的数据故事 + 轻量闭环
"""
from __future__ import annotations
import uuid

from ..base import BaseAgent
from tools import invoke_tool

STORYTELLING_AGENT_PROMPT = """# Role
你是 cocoBI 的数据分析报告编写专家,生成完整数据分析报告

# 输入
- 完整分析结果: {full_result}
- 用户上下文: {user_context}

# 输出(JSON)
{
  "reportTemplate": { ... },
  "observations": [...],
  "next_steps": [...],
  "recommended_followups": [...],
  "copy_insight_text": "..."
}

# 边界
- 不输出任何"立即执行 X""发送邮件给 Y""创建任务 Z"等可执行指令
- 所有观察点措辞:"建议关注""值得留意""可考虑"等中性表达
- 强提示(如"系统出错""数据异常")单独标注,不混入普通观察点
"""


class StorytellingAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="storytelling_agent", system_prompt=STORYTELLING_AGENT_PROMPT)

    async def run(self, full_result: dict, user_context: dict | None = None) -> dict:
        """生成数据故事 → 调用 render_chart → 调用 export_data_story"""
        story = await super().run(
            {"full_result": full_result, "user_context": user_context or {}}
        )

        story_id = f"story-{uuid.uuid4().hex[:8]}"
        story["story_id"] = story_id

        # 渲染图表 - PRD §3.2.2 重要约束:不执行任何外部动作
        sql_result = full_result.get("sql_result", {})
        rows = sql_result.get("rows", [])
        intent = full_result.get("intent", "QueryBasicMetrics")
        slots = full_result.get("slots", {})
        metric = slots.get("指标", "数量")
        time_range = slots.get("时间范围", "")

        charts = []
        if rows:
            # 趋势查询:用专门的折线图(短日期 M/D 格式)
            if intent == "QueryTrend":
                from services.llm_service import _build_trend_chart
                chart_result = _build_trend_chart(rows, metric, time_range)
                if chart_result.get("success"):
                    charts.append(chart_result)
            else:
                # 单值查询:主图用 render_chart (柱状),副图用每日趋势折线图
                # 智能 chart title:时间 + 维度 + 指标
                schema = full_result.get("schema", {})
                mapped = schema
                x_field = ""
                if rows:
                    # 从行里取第一个 key(类别字段名)
                    keys = list(rows[0].keys())
                    # 跳过纯数值字段
                    for k in keys:
                        v = rows[0].get(k)
                        if not isinstance(v, (int, float)):
                            x_field = k
                            break
                chart_title_parts = []
                if time_range and time_range not in ("", "全部时间", "最近7天"):
                    chart_title_parts.append(time_range)
                if x_field and x_field not in ("", metric):
                    chart_title_parts.append(x_field)
                chart_title_parts.append(metric)
                chart_title = "".join(chart_title_parts) if chart_title_parts else story.get("title", "")
                # 简化:6月+类别+销售额 → "6月产品类别销售额" (但去掉重复)
                # 实际更稳妥的:就用原 title,但给 chart 单独 title
                chart_title = story.get("title", "").replace("分析报告", "").strip() or "数据洞察"

                main_chart = await invoke_tool(
                    "render_chart",
                    data=rows,
                    chart_type="auto",
                    title=chart_title,
                )
                if main_chart.get("success"):
                    charts.append(main_chart)

                # 副图:按天趋势
                if intent in ("QueryUserCount", "QueryBasicMetrics"):
                    sub_chart = await self._build_daily_subchart(
                        full_result, metric, time_range, intent
                    )
                    if sub_chart and sub_chart.get("success"):
                        charts.append(sub_chart)

        story["charts"] = charts

        # 调用 generate_next_steps - 轻量闭环核心 - PRD §3.3.2 Tool 7
        ns_result = await invoke_tool(
            "generate_next_steps",
            story_context={"rows": rows},
            intent=full_result.get("intent", "QueryBasicMetrics"),
            slots=full_result.get("slots", {}),
        )
        story["next_steps"] = ns_result.get("next_steps", [])
        story["recommended_followups"] = ns_result.get("recommended_followups", [])

        # 导出(生成 share_url)
        export_result = await invoke_tool("export_data_story", story=story)
        if export_result.get("share_url"):
            story["share_url"] = export_result["share_url"]

        return story

    async def _build_daily_subchart(
        self, full_result: dict, metric: str, time_range: str, intent: str
    ) -> dict | None:
        """为单值查询构造一个按天趋势的副图(折线图)

        关键:复用 schema agent 已经生成的 filters(包括 is_valid=1 等默认过滤)
        """
        from services.llm_service import _build_trend_chart
        from tools import invoke_tool
        from services.llm_service import _mock_nl2sql

        schema = full_result.get("schema", {})
        time_field = schema.get("time_field", "")
        if not time_field:
            return None

        # 关键:复用 schema 已经生成的完整 filters(包含默认 is_valid=1)
        # 而不是只复用 intent 阶段提取的 filters
        schema_filters = schema.get("filters", [])
        # 去掉时间范围(趋势图要看完整周期)
        schema_filters_no_time = [
            f for f in schema_filters
            if f.get("field") != time_field
        ]

        slots = full_result.get("slots", {})
        # 把完整 filters 注入 slots
        slots_with_full_filters = dict(slots)
        slots_with_full_filters["filters"] = schema_filters_no_time

        nl_input = {
            "intent": "QueryTrend",
            "slots": slots_with_full_filters,
            "mapped_query": schema,
            "user_input": full_result.get("user_input", ""),
        }
        result = _mock_nl2sql(nl_input)
        sql = result.get("sql", "")
        if not sql:
            return None

        dataset_id = full_result.get("dataset_id", "")

        exec_result = await invoke_tool("execute_sql", sql=sql, dataset_id=dataset_id)
        if not exec_result.get("success"):
            return None

        rows = exec_result.get("rows", [])
        if not rows:
            return None

        sub_metric = "用户数" if intent == "QueryUserCount" else metric
        return _build_trend_chart(rows, sub_metric, time_range)
