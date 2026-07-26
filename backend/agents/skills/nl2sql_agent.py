"""Agent 3: NL2SQLAgent - 自然语言 → SQL (PRD §3.2.2)
基于 Schema 映射生成可执行 SQL
"""
from __future__ import annotations
from ..base import BaseAgent
from tools import invoke_tool
from config import FALLBACK_PROMPTS

NL2SQL_AGENT_PROMPT = """# Role
你是 cocoBI 的 NL2SQL 专家,基于 Schema 映射生成 SQL。

# 输入
- 意图: {intent}
- 槽位: {slots}
- 已映射 Schema: {mapped_query}

# 输出(JSON)
{
  "sql": "SELECT ...",
  "params": {},
  "explanation": "为什么这样写",
  "confidence": 0.0-1.0,
  "is_executable": true 或 false,
  "validation_errors": []
}

# SQL 规范
- 只用 SELECT,不允许 DROP、DELETE、UPDATE
- 必须带 LIMIT(默认 1000)
- 时间字段用 ISO 8601 格式
- 字段引用必须用反引号
- 遇到 JOIN 时,显式声明 ON

# Few-shot 示例
输入 mapped_query: {tables: ["orders"], fields: ["SUM(order_amount)"], filters: [{date >= '2026-07-13'}]}
输出: {
  "sql": "SELECT SUM(`order_amount`) AS gmv FROM `orders` WHERE `order_date` >= '2026-07-13' LIMIT 1000",
  "params": {},
  "confidence": 0.95,
  "is_executable": true,
  "validation_errors": []
}

# 边界
- 复杂查询(超过 5 个 JOIN)要降级为多次简单查询
- 检测到可疑操作(DROP、DELETE 等)直接返回 is_executable=false
"""


class NL2SQLAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(name="nl2sql_agent", system_prompt=NL2SQL_AGENT_PROMPT)

    async def run(self, intent: str, slots: dict, mapped_query: dict, dataset_id: str) -> dict:
        """生成 SQL - 失败时重试 3 次 → 降级为兜底 - PRD §3.1.5"""
        last_error = None
        for attempt in range(3):
            result = await super().run(
                {"intent": intent, "slots": slots, "mapped_query": mapped_query}
            )

            # 校验
            sql = result.get("sql", "")
            if not sql:
                last_error = "未生成 SQL"
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

        # 三次失败 → 兜底
        return {
            "sql": "",
            "params": {},
            "explanation": "SQL 生成失败",
            "confidence": 0.0,
            "is_executable": False,
            "validation_errors": [last_error] if last_error else [],
            "fallback_message": FALLBACK_PROMPTS["sql_failed"],
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
