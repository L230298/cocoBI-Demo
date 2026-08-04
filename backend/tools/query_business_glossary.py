"""Tool 5: query_business_glossary - 业务术语查询 (PRD §3.3.2)
跨行业,从当前数据集的行业模板加载术语库,返回定义/公式/示例。
用于 Interpretation / Attribution Agent 标准化表述;并被 SchemaAgent 在映射前调用。
"""
from __future__ import annotations
from .registry import register_tool
from services.glossary_service import lookup_term, get_glossary_for_industry, search_terms


@register_tool(
    name="query_business_glossary",
    purpose="查询业务术语定义、计算公式、示例(跨行业,从当前数据上传时的行业模板加载);用于解读和归因",
    owner_skills=["schema_agent", "interpretation_agent", "attribution_agent"],
    input_schema={
        "term": "string (必填,术语或关键词)",
        "industry_template": "string (选填,默认 '通用')",
        "mode": "string (选填: 'exact' 精确匹配 / 'fuzzy' 模糊搜索;默认 fuzzy)",
    },
    output_schema={
        "success": "bool",
        "terms": "list[{term, definition, formula, fields, examples, threshold}]",
    },
)
def query_business_glossary(
    term: str | None = None,
    industry_template: str = "通用",
    mode: str = "fuzzy",
) -> dict:
    """查询业务术语库

    mode=exact: 精确或别名匹配单个术语
    mode=fuzzy: 模糊搜索,返回所有匹配的术语(用于 SchemaAgent 兜底)
    """
    if not term:
        return {"success": False, "error_code": "BadRequest", "error_msg": "term 必填"}

    if mode == "exact":
        info = lookup_term(term, industry_template)
        if not info:
            return {"success": True, "terms": []}
        return {"success": True, "terms": [info]}

    # fuzzy
    hits = search_terms(term, industry_template)
    return {"success": True, "terms": hits}