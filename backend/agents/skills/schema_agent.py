"""Agent 2: SchemaAgent - Schema 映射 (PRD §3.2.2)
业务术语 → 数据库 Schema

P0-1 升级:
1. SchemaAgent 在映射前先调用 query_business_glossary 工具
2. 如果用户的 metric/槽位匹配到业务术语,直接采用术语的 formula/fields,不再瞎映射
3. Prompt 强化"业务术语优先"规则
"""
from __future__ import annotations
from ..base import BaseAgent
from tools import invoke_tool


SCHEMA_AGENT_PROMPT = """# Role
你是 cocoBI 的 Schema 映射助手,负责把业务术语翻译成数据库 Schema。

# 核心规则:业务术语优先 (P0-1 升级)
- 你已经获得了 query_business_glossary 工具返回的 terms 列表
- 如果用户的"指标"/"维度"在 terms 中,必须使用其 formula 涉及的 fields,不要瞎映射到相似字段
- 例如:用户问"库存" → terms 里有"库存"定义 stock 字段 → 必须用 stock,不能用 orders.category 替代

# 输入
- 意图与槽位: {slots}
- 数据源元数据: {data_source_metadata}
- 业务术语库 (query_business_glossary 返回): {matched_terms}

# 输出(JSON)
{
  "tables": ["表1", "表2"],
  "fields": ["field1", "field2"],
  "filters": [{"field": "order_date", "op": ">=", "value": "2026-07-13"}],
  "unmapped_slots": ["未映射的业务术语"],
  "confidence": 0.0-1.0,
  "term_mappings": {"用户提到的业务词": "对应公式"}
}

# Few-shot 示例
输入 slots: {"指标": "有效订单"}
matched_terms: [{"term": "有效订单", "formula": "order_status='paid' AND refund_status='none'", "fields": ["order_status","refund_status"]}]
输出: {
  "tables": ["orders"],
  "fields": ["order_id", "order_status", "refund_status"],
  "filters": [{"field": "order_status", "op": "=", "value": "paid"}, ...],
  "unmapped_slots": [],
  "confidence": 0.93,
  "term_mappings": {"有效订单": "order_status='paid' AND refund_status='none'"}
}

# Few-shot 2: 业务术语纠正
输入 slots: {"指标": "库存"}
matched_terms: [{"term": "库存", "formula": "SUM(`stock`)", "fields": ["stock","sku"]}]
输出: {
  "tables": ["inventory"],  // 或 dataset 实际表
  "fields": ["stock", "sku"],
  "filters": [],
  "unmapped_slots": [],
  "confidence": 0.9,
  "term_mappings": {"库存": "SUM(`stock`)"}
}

# 边界
- 不直接生成 SQL,只输出字段映射
- 未在术语库中的术语,unmapped_slots 列出,confidence < 0.8
- 如果 matched_terms 为空,按字段名相似度兜底
"""


class SchemaAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="schema_agent", system_prompt=SCHEMA_AGENT_PROMPT)

    async def run(self, intent: str, slots: dict, dataset_id: str) -> dict:
        """P0-1 升级: 调用 get_data_source_metadata + query_business_glossary → LLM 映射

        增强:
        - 业务术语优先:先查术语库,把命中结果喂给 LLM
        - 数据清洗默认:is_valid 字段自动 is_valid=1
        """
        # 1. 拉数据源元数据
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

        # 2. P0-1 升级:查业务术语库
        industry = (metadata.get("business_glossary") or {}).get("_industry", "通用")
        # 从 dataset metadata 推断 industry_template
        # 实际项目里 dataset_registry 会带这个字段,这里兜底用 "通用"
        industry = industry or "通用"

        # 抽取用户提到的关键业务词(指标 + 时间范围 + 维度)
        metric = slots.get("指标", "")
        user_terms_to_lookup = []
        if metric and metric not in ("GMV", "数量"):  # GMV/数量是兜底,不再查
            user_terms_to_lookup.append(metric)

        matched_terms: list[dict] = []
        for t in user_terms_to_lookup:
            res = await invoke_tool(
                "query_business_glossary",
                term=t,
                industry_template=industry,
                mode="fuzzy",
            )
            if res.get("success"):
                matched_terms.extend(res.get("terms", []))

        # 3. 调用 LLM 做映射(传入 matched_terms)
        result = await super().run(
            {
                "intent": intent,
                "slots": slots,
                "data_source_metadata": metadata.get("tables", []),
                "business_glossary": metadata.get("business_glossary", {}),
                "matched_terms": matched_terms,
            }
        )

        # P0-1 数据降级: 如果 matched_terms 命中了业务术语,但 LLM 没采用任何 term_mappings 的 fields
        # 给用户友好提示而不是静默降级到无关字段
        if matched_terms and result.get("success") is not False:
            mapped_fields = set(result.get("fields", []))
            used_term_fields = set()
            for t in matched_terms:
                used_term_fields.update(t.get("fields", []))
            # 如果术语需要 stock/safety_stock 等字段,但 mapping 出来的 fields 一个都没有
            if used_term_fields and not (mapped_fields & used_term_fields):
                # 数据集缺字段,返回友好提示
                missing_terms = [t["term"] for t in matched_terms]
                return {
                    "tables": [],
                    "fields": [],
                    "filters": [],
                    "joins": [],
                    "unmapped_slots": list(slots.keys()),
                    "term_mappings": {t["term"]: t.get("formula", "") for t in matched_terms},
                    "confidence": 0.0,
                    "fallback_message": (
                        f"数据集不支持以下分析: {', '.join(missing_terms)}。"
                        f"当前数据集字段: {', '.join(mapped_fields) if mapped_fields else '无'}。"
                        f"建议上传包含 {', '.join(sorted(used_term_fields))} 字段的数据集。"
                    ),
                }

        # 4. 数据清洗默认(保留原有行为)
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
                result["filters"] = result.get("filters", []) + [
                    {"field": "is_valid", "op": "=", "value": 1}
                ]
                result["_default_filter_applied"] = "is_valid=1 (数据清洗默认)"

        # 5. P0-1 增补:在 result 里记录术语映射(便于 NL2SQL 和埋点)
        if matched_terms:
            result["term_mappings"] = {
                t["term"]: t.get("formula", "") for t in matched_terms
            }

        return result