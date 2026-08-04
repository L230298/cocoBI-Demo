"""Agent 3: NL2SQLAgent - 自然语言 → SQL (PRD §3.2.2)
基于 Schema 映射生成可执行 SQL
"""
from __future__ import annotations
from ..base import BaseAgent
from tools import invoke_tool
from config import FALLBACK_PROMPTS

NL2SQL_AGENT_PROMPT = """# Role
你是 cocoBI 的 NL2SQL 专家,基于 Schema 映射生成 SQL。

# 核心规则:业务术语计算公式优先 (P0-1 升级)
- 你已经获得了 term_mappings (业务术语 → SQL 公式)
- 当 SQL 涉及业务术语(库存/客单价/复购率/转化率/GMV 等)时,必须严格使用 term_mappings 里的 formula
- 不要把"库存"用 orders 表的 SUM(amount) 替代,这是 P0-1 的核心修复点

# 输入
- 意图: {intent}
- 槽位: {slots}
- 已映射 Schema: {mapped_query}
- 业务术语公式: {term_mappings}

# 输出(JSON)
{
  "sql": "SELECT ...",
  "params": {},
  "explanation": "为什么这样写 (引用了哪些业务术语公式)",
  "confidence": 0.0-1.0,
  "is_executable": true 或 false,
  "validation_errors": [],
  "terms_used": ["库存", "客单价"]  // 本次 SQL 用到的业务术语
}

# SQL 规范
- 只用 SELECT,不允许 DROP、DELETE、UPDATE
- 必须带 LIMIT(默认 1000)
- 时间字段用 ISO 8601 格式
- 字段引用必须用反引号
- 遇到 JOIN 时,显式声明 ON

# Few-shot 示例 (业务术语)
输入 mapped_query: {tables: ["inventory"], fields: ["stock","sku"], filters: [{stock < 100}]}
term_mappings: {"库存": "SUM(`stock`)", "安全库存": "`safety_stock`"}
输出: {
  "sql": "SELECT `sku`, `stock`, `safety_stock` FROM `inventory` WHERE `stock` < `safety_stock` ORDER BY (`safety_stock` - `stock`) DESC LIMIT 100",
  "params": {},
  "explanation": "使用业务术语'库存'的 SUM(stock) 公式,以及'安全库存'的 safety_stock 阈值字段,筛选库存量低于安全线的 SKU",
  "confidence": 0.95,
  "is_executable": true,
  "validation_errors": [],
  "terms_used": ["库存", "安全库存"]
}

# 边界
- 复杂查询(超过 5 个 JOIN)要降级为多次简单查询
- 检测到可疑操作(DROP、DELETE 等)直接返回 is_executable=false
"""


class NL2SQLAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="nl2sql_agent", system_prompt=NL2SQL_AGENT_PROMPT)

    async def run(self, intent: str, slots: dict, mapped_query: dict, dataset_id: str, user_input: str = "") -> dict:
        """P0-1.4 升级: SQL 生成时把 term_mappings 喂给 LLM,业务术语公式优先

        生成 SQL - 失败时重试 3 次 → 降级为兜底 - PRD §3.1.5
        """
        last_error = None
        last_fallback_message = None  # Bug #2: 保留内层 fallback_message (数据集缺字段等场景)
        for attempt in range(3):
            result = await super().run(
                {
                    "intent": intent,
                    "slots": slots,
                    "mapped_query": mapped_query,
                    "user_input": user_input,
                    "term_mappings": mapped_query.get("term_mappings", {}) if isinstance(mapped_query, dict) else {},
                }
            )

            # Bug #2: 内层已有友好 fallback_message (例如数据集缺 amount 字段),直接返回
            if result.get("fallback_message") and not result.get("is_executable", True):
                return result

            # 校验
            sql = result.get("sql", "")
            if not sql:
                last_error = "未生成 SQL"
                last_fallback_message = result.get("fallback_message")
                continue

            # 快速执行校验
            exec_result = await invoke_tool("execute_sql", sql=sql, dataset_id=dataset_id)
            if exec_result.get("success"):
                # 格式化 SQL(多行 + 关键字大写)
                formatted_sql = _format_sql(sql)
                result["sql"] = formatted_sql
                result["sample_result"] = exec_result
                return result

            last_error = exec_result.get("error_msg", "未知错误")
            last_fallback_message = result.get("fallback_message")

        # 三次失败 → 兜底
        # Bug #2: 如果内层有友好提示(如缺字段),优先使用;否则用通用兜底
        final_fallback = last_fallback_message or FALLBACK_PROMPTS["sql_failed"]
        return {
            "sql": "",
            "params": {},
            "explanation": "SQL 生成失败",
            "confidence": 0.0,
            "is_executable": False,
            "validation_errors": [last_error] if last_error else [],
            "fallback_message": final_fallback,
        }


def _format_sql(sql: str) -> str:
    """把单行 SQL 格式化为多行可读格式"""
    import re

    if not sql:
        return sql

    # 关键字大写
    keywords = ["SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING",
                "LIMIT", "AND", "OR", "AS", "DISTINCT", "COUNT", "SUM",
                "AVG", "MIN", "MAX", "DESC", "ASC", "ON", "JOIN", "LEFT JOIN",
                "RIGHT JOIN", "INNER JOIN", "CASE", "WHEN", "THEN", "ELSE", "END"]
    formatted = sql
    for kw in sorted(keywords, key=len, reverse=True):
        # 用正则替换,只匹配整词
        pattern = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        formatted = pattern.sub(kw, formatted)

    # 主要子句前换行
    for kw in ["FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING", "LIMIT"]:
        formatted = re.sub(r"\s+" + kw + r"\b", "\n" + kw, formatted, flags=re.IGNORECASE)

    # AND/OR 换行缩进
    formatted = re.sub(r"\s+AND\s+", "\n  AND ", formatted, flags=re.IGNORECASE)
    formatted = re.sub(r"\s+OR\s+", "\n  OR ", formatted, flags=re.IGNORECASE)

    # SELECT 后的字段换行(逗号后)
    formatted = re.sub(r"SELECT\s+", "SELECT\n  ", formatted, flags=re.IGNORECASE)

    return formatted.strip()
