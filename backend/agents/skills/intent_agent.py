"""Agent 1: IntentAgent - 意图分类 (PRD §3.2.2)
识别用户自然语言意图,提取槽位,给出置信度
"""
from __future__ import annotations
from ..base import BaseAgent
from config import FALLBACK_PROMPTS

INTENT_AGENT_PROMPT = """# Role
你是 cocoBI 的意图分类助手,负责识别业务人员用自然语言表达的分析诉求。

# ⚠️ P0-2 关键约束: 意图枚举边界 (PRD §3.1.4)
intent 必须是以下 6 个字符串之一,严禁发明新意图:
  - QueryBasicMetrics         (基础问数,查单值指标)
  - QueryCompareAndTopN       (多维对比与TopN,排序/排名/对比)
  - ThresholdAlert            (阈值预警,低于/超过/异常)
  - AttributeAnalysis         (归因分析,为什么掉/为什么涨)
  - SmartInterpretation       (智能解读,解释/解读/说明)
  - Unknown                   (无法识别时用 Unknown,confidence < 0.5)

趋势类问题(每日/按日/走势/随时间变化)请归到 QueryCompareAndTopN(添加 dimension=date/time),
或归到 SmartInterpretation(让解读 Agent 跑一遍)。
不要输出 QueryTrend / QueryUserCount / 其他任何自定义意图名。

# 输入
- 用户当前输入: {user_input}
- 对话历史: {session_history}

# 输出格式(JSON)
{
  "intent": "枚举值之一",
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

示例 4 (趋势 → 归并):
输入: "请帮我分析最近 30 天的销售走势"
输出: {"intent": "QueryCompareAndTopN", "confidence": 0.9, "slots": {"指标": "GMV", "时间范围": "最近30天", "维度": "date"}, "alternatives": ["SmartInterpretation"]}

# 边界与禁止
- 不识别未在术语表中的指标 → slots 留空并降低 confidence
- 不解读数据 → 仅返回结构化意图
- intent 不确定时,confidence < 0.7,alternatives 给出 Top-3 候选
- 严禁输出 QueryTrend / QueryUserCount 等 PRD 未定义的意图名(系统在 Python 层会强制改写为 Unknown)
"""


# P0-2: 意图枚举白名单
ALLOWED_INTENTS = frozenset({
    "QueryBasicMetrics",
    "QueryCompareAndTopN",
    "ThresholdAlert",
    "AttributeAnalysis",
    "SmartInterpretation",
    "Unknown",
})


class IntentAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="intent_agent", system_prompt=INTENT_AGENT_PROMPT)

    async def run(self, user_input: str, session_history: list | None = None) -> dict:
        """P0-2 升级: 枚举边界校验 + 兜底处理

        - 如果 LLM 返回的 intent 不在 ALLOWED_INTENTS,强制改写为 Unknown
        - intent=Unknown 时 confidence 强制 < 0.5
        - confidence < 0.7 时给 fallback_message
        """
        result = await super().run(
            {"user_input": user_input, "session_history": session_history or []}
        )

        # P0-2 关键:枚举校验,非白名单 intent 强制改写为 Unknown
        raw_intent = result.get("intent", "")
        if raw_intent not in ALLOWED_INTENTS:
            result["original_intent"] = raw_intent  # 记录原始值,便于调试
            result["intent"] = "Unknown"
            result["confidence"] = min(result.get("confidence", 0.0), 0.4)

        # alternatives 也要校验
        alts = result.get("alternatives", [])
        if isinstance(alts, list):
            result["alternatives"] = [a for a in alts if a in ALLOWED_INTENTS]

        # 兜底:意图置信度 < 0.7 → 提供候选项 + 兜底文案
        if result.get("confidence", 1.0) < 0.7:
            result["fallback_message"] = FALLBACK_PROMPTS["intent_unknown"]

        return result
