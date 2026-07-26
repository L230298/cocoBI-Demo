"""Tool 7: generate_next_steps - 下一步建议与推荐追问 (PRD §3.3.2)
轻量闭环核心:纯文字生成,绝不调用外部 API
"""
from __future__ import annotations
from .registry import register_tool


@register_tool(
    name="generate_next_steps",
    purpose="基于数据故事结果,生成下一步建议(纯文字)和推荐追问(可点选填入)",
    owner_skills=["storytelling_agent"],
    input_schema={"story_context": "object", "intent": "string", "slots": "object"},
    output_schema={
        "next_steps": "list[{text, type}]",
        "recommended_followups": "list[{text, intent_hint}]",
    },
)
def generate_next_steps(story_context: dict, intent: str = "QueryBasicMetrics", slots: dict | None = None) -> dict:
    """轻量闭环 - 纯文字生成 - 绝不触发外部动作"""
    slots = slots or {}
    metric = slots.get("指标", "数据")
    time_range = slots.get("时间范围", "最近7天")

    # 不同意图生成不同建议 - PRD §3.2.2 Agent4
    next_steps_by_intent = {
        "QueryBasicMetrics": [
            {"text": f"建议关注 {metric} 同期对比变化", "type": "compare"},
            {"text": f"可按品类/渠道拆解 {metric}", "type": "drill"},
            {"text": "可分享到团队,辅助决策", "type": "share"},
        ],
        "QueryCompareAndTopN": [
            {"text": "建议导出排行榜用于复盘", "type": "export"},
            {"text": "可查看排名末尾的对象详情", "type": "drill"},
        ],
        "ThresholdAlert": [
            {"text": "建议立即查看异常对象详情", "type": "drill"},
            {"text": "可设置监控定时推送", "type": "explore"},
        ],
        "AttributeAnalysis": [
            {"text": "建议团队评审归因结论", "type": "explore"},
            {"text": "可导出为周报素材", "type": "share"},
            {"text": f"可对比去年同期 {metric} 表现", "type": "compare"},
        ],
        "SmartInterpretation": [
            {"text": f"建议对比上一周期 {metric}", "type": "compare"},
            {"text": "可分享到团队", "type": "share"},
        ],
    }
    next_steps = next_steps_by_intent.get(
        intent,
        [{"text": "建议对比上一周期", "type": "compare"}, {"text": "可分享到团队", "type": "share"}],
    )

    # 推荐追问 - 2-4 条 - PRD §1.2
    followups_pool = [
        {"text": f"为什么 {metric} 会这样变化?", "intent_hint": "AttributeAnalysis"},
        {"text": f"分品类看看 {metric} 表现", "intent_hint": "QueryCompareAndTopN"},
        {"text": f"对比上一周期 {metric}", "intent_hint": "QueryCompareAndTopN"},
        {"text": f"{metric} 有异常吗?", "intent_hint": "ThresholdAlert"},
        {"text": f"近 30 天 {metric} 趋势", "intent_hint": "QueryBasicMetrics"},
    ]
    recommended_followups = followups_pool[:4]

    return {
        "success": True,
        "next_steps": next_steps[:5],
        "recommended_followups": recommended_followups[:4],
    }
