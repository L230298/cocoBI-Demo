"""业务术语库 - PRD §3.3.2 Tool 5 query_business_glossary 的数据源

按行业模板分类,提供术语定义 + 计算公式 + 示例。
为 P0-1 (业务术语库 + Schema 映射升级) 提供基础数据。

设计原则:
1. 通用术语 (industry_template='通用') 跨行业可用
2. 行业术语按 PRD §3.4 划分:零售、电商、制造、教育
3. 每个术语包含:
   - term: 业务名称
   - definition: 用户友好的定义
   - formula: 计算公式(SQL 片段)
   - fields: 涉及字段
   - examples: 用户常见问法
   - threshold: 可选,默认阈值(用于 I3 阈值预警)
"""
from __future__ import annotations
from typing import Any


# ==================== 通用术语库 ====================
GENERAL_GLOSSARY: dict[str, dict[str, Any]] = {
    "GMV": {
        "term": "GMV",
        "definition": "商品总销售额(Gross Merchandise Value),成交总额,不含退款",
        "formula": "SUM(`amount`)",
        "fields": ["amount", "status"],
        "examples": ["GMV", "销售额", "成交总额", "营收"],
        "default_filter": {"field": "status", "op": "=", "value": "已支付"},
    },
    "订单量": {
        "term": "订单量",
        "definition": "订单总笔数(可按已支付/已发货等状态过滤)",
        "formula": "COUNT(DISTINCT `order_id`)",
        "fields": ["order_id"],
        "examples": ["订单数", "订单量", "单量", "销量"],
    },
    "用户数": {
        "term": "用户数",
        "definition": "去重用户数(购买用户 / 活跃用户)",
        "formula": "COUNT(DISTINCT `user_id`)",
        "fields": ["user_id"],
        "examples": ["用户", "客户", "人数", "买家"],
    },
    "客单价": {
        "term": "客单价",
        "definition": "平均每个用户的销售额 = 总销售额 / 用户数",
        "formula": "SUM(`amount`) / NULLIF(COUNT(DISTINCT `user_id`), 0)",
        "fields": ["amount", "user_id"],
        "examples": ["客单价", "客单"],
    },
    "复购率": {
        "term": "复购率",
        "definition": "购买 ≥ 2 次的用户数 / 总用户数",
        "formula": (
            "100.0 * COUNT(DISTINCT CASE WHEN order_count >= 2 THEN user_id END) "
            "/ NULLIF(COUNT(DISTINCT user_id), 0)"
        ),
        "fields": ["user_id"],
        "examples": ["复购", "回购", "复购率"],
    },
    "转化率": {
        "term": "转化率",
        "definition": "转化数 / 访问数(需数据集有 visit/conversion 字段)",
        "formula": "SUM(`conversion_count`) / NULLIF(SUM(`visit_count`), 0)",
        "fields": ["conversion_count", "visit_count"],
        "examples": ["转化率", "转化"],
    },
    "库存": {
        "term": "库存",
        "definition": "SKU 当前库存量(需数据集有 stock 字段)",
        "formula": "SUM(`stock`)",
        "fields": ["stock", "sku"],
        "examples": ["库存", "存货", "库存量"],
    },
    "安全库存": {
        "term": "安全库存",
        "definition": "SKU 安全库存阈值(需数据集有 safety_stock 字段)",
        "formula": "`safety_stock`",
        "fields": ["safety_stock", "sku"],
        "examples": ["安全库存", "安全线"],
    },
    "毛利率": {
        "term": "毛利率",
        "definition": "(销售额 - 成本) / 销售额",
        "formula": "1 - SUM(`cost`) / NULLIF(SUM(`amount`), 0)",
        "fields": ["amount", "cost"],
        "examples": ["毛利", "毛利率", "利润率"],
    },
}


# ==================== 零售行业术语 ====================
RETAIL_GLOSSARY: dict[str, dict[str, Any]] = {
    "畅销品": {
        "term": "畅销品",
        "definition": "按销售额或销量排序的 TOP 商品",
        "formula": "ORDER BY SUM(`amount`) DESC LIMIT 10",
        "fields": ["sku", "amount"],
        "examples": ["畅销品", "热卖商品", "卖得好的"],
    },
    "滞销品": {
        "term": "滞销品",
        "definition": "销量低于某阈值或排在尾部的商品",
        "formula": "ORDER BY SUM(`amount`) ASC LIMIT 10",
        "fields": ["sku", "amount"],
        "examples": ["滞销品", "卖不动的", "低销"],
    },
    "坪效": {
        "term": "坪效",
        "definition": "单位面积的销售额(需 dataset 有 area 字段)",
        "formula": "SUM(`amount`) / NULLIF(SUM(`area`), 0)",
        "fields": ["amount", "area", "store"],
        "examples": ["坪效"],
    },
}


# ==================== 行业模板 → 术语库映射 ====================
INDUSTRY_GLOSSARY: dict[str, dict[str, dict[str, Any]]] = {
    "通用": GENERAL_GLOSSARY,
    "零售": {**GENERAL_GLOSSARY, **RETAIL_GLOSSARY},
    # 电商 / 制造 / 教育 暂复用通用,后续版本再扩展
    "电商": GENERAL_GLOSSARY,
    "制造": GENERAL_GLOSSARY,
    "教育": GENERAL_GLOSSARY,
}


def lookup_term(term: str, industry_template: str = "通用") -> dict | None:
    """查找单个术语(大小写不敏感 + 别名匹配)"""
    glossary = INDUSTRY_GLOSSARY.get(industry_template) or INDUSTRY_GLOSSARY["通用"]
    term_lower = term.lower().strip()
    # 1) 直接匹配
    if term in glossary:
        return glossary[term]
    # 2) 遍历 examples 找别名
    for canonical, info in glossary.items():
        aliases = [canonical.lower()] + [ex.lower() for ex in info.get("examples", [])]
        if term_lower in aliases:
            return info
    return None


def get_glossary_for_industry(industry_template: str = "通用") -> dict[str, dict[str, Any]]:
    """返回指定行业的完整术语库(给 SchemaAgent 看)"""
    return INDUSTRY_GLOSSARY.get(industry_template) or INDUSTRY_GLOSSARY["通用"]


def search_terms(query: str, industry_template: str = "通用") -> list[dict]:
    """搜索包含关键词的所有术语(模糊匹配 examples)"""
    glossary = get_glossary_for_industry(industry_template)
    query_lower = query.lower()
    hits = []
    for canonical, info in glossary.items():
        if query_lower in canonical.lower() or any(query_lower in ex.lower() for ex in info.get("examples", [])):
            hits.append(info)
    return hits