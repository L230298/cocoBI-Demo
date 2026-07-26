"""Agent 1: IntentAgent - 意图分类 (PRD §3.2.2)
识别用户自然语言意图,提取槽位,给出置信度
"""
from __future__ import annotations
from ..base import BaseAgent
from config import FALLBACK_PROMPTS

INTENT_AGENT_PROMPT = """# Role
你是 cocoBI 的意图分类助手,负责识别业务人员用自然语言表达的分析诉求。

# 输入
- 用户当前输入: {user_input}
- 对话历史: {session_history}

# 输出格式(JSON)
{
  "intent": "意图ID,从以下选择:QueryBasicMetrics | QueryCompareAndTopN | ThresholdAlert | AttributeAnalysis | SmartInterpretation | Unknown",
  "confidence": 0.0-1.0,
  "slots": {
    "指标": "...",
    "时间范围": "...",
    "TOP_N": "...",
    "对比基准": "..."
  },
  "alternatives": ["意图ID1", "意图ID2"]
}

# Few-shot 示例
示例 1:
输入: "上周 GMV 是多少?"
输出: {"intent": "QueryBasicMetrics", "confidence": 0.95, "slots": {"指标": "GMV", "时间范围": "上周"}, "alternatives": []}

示例 2:
输入: "为什么这个月订单掉了?"
输出: {"intent": "AttributeAnalysis", "confidence": 0.92, "slots": {"指标": "订单量", "时间范围": "本月", "对比基准": "上月"}, "alternatives": ["QueryBasicMetrics"]}

示例 3:
输入: "最近什么卖得好?"
输出: {"intent": "QueryCompareAndTopN", "confidence": 0.88, "slots": {"时间范围": "最近"}, "alternatives": ["QueryBasicMetrics"]}

# 边界与禁止
- 不识别未在术语表中的指标 → slots 留空并降低 confidence
- 不解读数据 → 仅返回结构化意图
- intent 不确定时,confidence < 0.7,alternatives 给出 Top-3 候选
"""


class IntentAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="intent_agent", system_prompt=INTENT_AGENT_PROMPT)

    async def run(self, user_input: str, session_history: list | None = None) -> dict:
        """识别意图 + 兜底处理 - PRD §3.1.5"""
        result = await super().run(
            {"user_input": user_input, "session_history": session_history or []}
        )

        # 兜底:意图置信度 < 0.7 → 提供候选项 + 兜底文案
        if result.get("confidence", 1.0) < 0.7:
            result["fallback_message"] = FALLBACK_PROMPTS["intent_unknown"]

        return result
