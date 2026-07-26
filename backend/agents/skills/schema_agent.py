"""Agent 2: SchemaAgent - Schema 映射 (PRD §3.2.2)
业务术语 → 数据库 Schema
"""
from __future__ import annotations
from ..base import BaseAgent
from tools import invoke_tool

SCHEMA_AGENT_PROMPT = """# Role
你是 cocoBI 的 Schema 映射助手,负责把业务术语翻译成数据库 Schema。

# 输入
- 意图与槽位: {slots}
- 数据源元数据: {data_source_metadata}
- 业务术语库: {business_glossary}

# 输出(JSON)
{
  "tables": ["表1", "表2"],
  "fields": ["field1", "field2"],
  "filters": [{"field": "order_date", "op": ">=", "value": "2026-07-13"}],
  "unmapped_slots": ["未映射的业务术语"],
  "confidence": 0.0-1.0
}

# Few-shot 示例
输入 slots: {"指标": "有效订单"}
business_glossary: {"有效订单": "order_status='paid' AND refund_status='none'"}
输出: {
  "tables": ["orders"],
  "fields": ["order_id", "order_status", "refund_status"],
  "filters": [{"field": "order_status", "op": "=", "value": "paid"}, ...],
  "unmapped_slots": [],
  "confidence": 0.93
}

# 边界
- 不直接生成 SQL,只输出字段映射
- 未在术语库中的术语,unmapped_slots 列出,confidence < 0.8
"""


class SchemaAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="schema_agent", system_prompt=SCHEMA_AGENT_PROMPT)

    async def run(self, intent: str, slots: dict, dataset_id: str) -> dict:
        """调用 get_data_source_metadata → LLM 映射

        增强:数据清洗原则 —— 如果数据集有 is_valid 字段,默认 is_valid=1
        用户说"无效"/"全部"时可覆盖
        """
        meta_result = await invoke_tool(
            "get_data_source_metadata", dataset_id=dataset_id
        )
        if not meta_result.get("success"):
            return {
                "tables": [],
                "fields": [],
                "filters": [],
                "joins": [],
                "unmapped_slots": list(slots.keys()),
                "confidence": 0.0,
                "error": meta_result.get("error_msg", "数据源未找到"),
            }

        metadata = meta_result
        result = await super().run(
            {
                "intent": intent,
                "slots": slots,
                "data_source_metadata": metadata.get("tables", []),
                "business_glossary": metadata.get("business_glossary", {}),
            }
        )

        # 数据清洗默认:如果数据集有 is_valid 字段,且用户没明确说"无效/全部/所有"
        if result.get("success") is not False:
            fields = result.get("fields", [])
            user_input = (slots.get("_user_input", "") or "").lower()
            user_filters = slots.get("filters", [])
            existing_is_valid = next(
                (f for f in user_filters if f.get("field") == "is_valid"),
                None,
            )

            if (
                "is_valid" in fields
                and existing_is_valid is None
                and not any(k in user_input for k in ["无效", "全部", "所有", "不过滤", "all", "raw"])
            ):
                # 默认:只算有效数据
                result["filters"] = result.get("filters", []) + [
                    {"field": "is_valid", "op": "=", "value": 1}
                ]
                result["_default_filter_applied"] = "is_valid=1 (数据清洗默认)"

        return result
