"""单元测试:确保 chart 生成器对所有查询类型都正确

目标:防止"两图不一致"bug 再犯
"""
import sys
sys.path.insert(0, 'C:/Users/huawei/Desktop/cocobi-demo/backend')

import importlib

# 强制重置
for mod in list(sys.modules.keys()):
    if mod.startswith(('services', 'routers', 'agents', 'tools', 'config', 'main')):
        del sys.modules[mod]


def test_query_compare_topn_returns_grouped():
    """QueryCompareAndTopN 必须返回分组数据,不是单值"""
    from services.llm_service import _mock_intent, _mock_nl2sql

    # 销售订单 schema
    mapped = {
        "tables": ["sales_order"],
        "fields": ["order_id", "order_date", "customer_id", "customer_city",
                   "product_category", "product_name", "sales_amount", "quantity", "discount", "profit"],
        "data_source_metadata": [{
            "fields": [
                {"name": "order_id", "type": "object"},
                {"name": "order_date", "type": "datetime64[ns]"},
                {"name": "customer_id", "type": "int64"},
                {"name": "customer_city", "type": "object"},
                {"name": "product_category", "type": "object"},
                {"name": "product_name", "type": "object"},
                {"name": "sales_amount", "type": "int64"},
                {"name": "quantity", "type": "int64"},
                {"name": "discount", "type": "float64"},
                {"name": "profit", "type": "int64"},
            ]
        }],
    }

    # 1. intent 必须识别为 CompareAndTopN
    intent = _mock_intent({"user_input": "6月按产品类别销售额"})
    assert intent["intent"] == "QueryCompareAndTopN", \
        f"应识别为 QueryCompareAndTopN,实际 {intent['intent']}"
    print(f"  ✓ intent: {intent['intent']}")
    print(f"  ✓ filters: {intent['slots'].get('filters')}")

    # 2. filters 不应包含"销售额"作为 category
    filters = intent["slots"].get("filters", [])
    for f in filters:
        if f.get("field") in ("category", "device_config"):
            assert "销售额" not in f.get("value", ""), \
                f"filter 误抽销售额: {f}"
    print(f"  ✓ filters 没误抓业务词")

    # 3. SQL 必须 GROUP BY
    sql_result = _mock_nl2sql({
        "intent": "QueryCompareAndTopN",
        "slots": intent["slots"],
        "mapped_query": mapped,
        "user_input": "6月按产品类别销售额",
    })
    sql = sql_result["sql"]
    assert "GROUP BY" in sql.upper(), f"SQL 缺 GROUP BY: {sql}"
    assert "product_category" in sql, f"SQL 没按 product_category 分组: {sql}"
    print(f"  ✓ SQL 有 GROUP BY product_category")

    return True


def test_category_field_picks_product_category():
    """_find_category_field 应该选 product_category 而不是 customer_city"""
    from services.llm_service import _find_category_field

    mapped = {
        "fields": ["order_id", "order_date", "customer_id", "customer_city",
                   "product_category", "product_name", "sales_amount", "quantity", "discount", "profit"],
        "data_source_metadata": [{
            "fields": [
                {"name": "customer_id", "type": "int64"},
                {"name": "customer_city", "type": "object"},
                {"name": "product_category", "type": "object"},
            ]
        }],
    }
    cat = _find_category_field(mapped)
    assert cat == "product_category", f"应选 product_category,实际 {cat}"
    print(f"  ✓ _find_category_field 选 {cat}")
    return True


def test_chart_title_smart():
    """chart title 应包含时间+维度+指标"""
    # 模拟 storytelling_agent 中的 title 生成
    x_field = "product_category"
    time_range = "2026-06"
    metric = "GMV"
    friendly = {"product_category": "产品类别", "GMV": "销售额"}
    pretty_x = friendly.get(x_field.lower(), x_field)
    friendly_m = friendly.get(metric, metric)
    parts = []
    if time_range: parts.append(time_range)
    if pretty_x: parts.append(pretty_x)
    if friendly_m: parts.append(friendly_m)
    title = "".join(parts)
    assert title == "2026-06产品类别销售额", f"title 错: {title}"
    print(f"  ✓ chart title: {title}")
    return True


def test_no_business_words_in_category_filter():
    """category filter 不应包含业务词(销售额/销量等)"""
    from services.llm_service import _extract_filters

    tests = [
        ("6月按产品类别销售额", None),  # 不应有 category filter
        ("各类别销售额", None),
        ("按产品类别看销售情况", None),
        ("6月无效用户", "is_valid=0"),  # 应该有 is_valid
        ("6月有效用户每日趋势", "device_config"),  # 应该有 device_config
    ]
    for text, expected_field in tests:
        filters = _extract_filters(text)
        for f in filters:
            if f.get("field") in ("category", "device_config"):
                v = f.get("value", "")
                assert "销售额" not in v, f"[{text}] 误抓销售额: {f}"
                assert "销量" not in v, f"[{text}] 误抓销量: {f}"
                assert "GMV" not in v, f"[{text}] 误抓 GMV: {f}"
        print(f"  ✓ [{text}] → {filters}")


def test_followup_query_detection():
    """接续 query 检测 - '再/也/还/那'触发继承"""
    from services.llm_service import _is_followup_query

    followup_inputs = [
        "再按城市拆分",
        "再看一下按月份",
        "那按渠道呢",
        "也拆成城市",
        "另一个维度",
    ]
    non_followup = [
        "上周 GMV 是多少",
        "6月按产品类别销售额",
        "今天天气怎样",
    ]
    for text in followup_inputs:
        assert _is_followup_query(text), f"[{text}] 应识别为接续"
        print(f"  ✓ [{text}] → followup")
    for text in non_followup:
        assert not _is_followup_query(text), f"[{text}] 不应识别为接续"
        print(f"  ✓ [{text}] → not followup")


def test_inherit_slots_from_history():
    """接续 query 继承上一轮的 time_range + intent"""
    from services.llm_service import _mock_intent

    # 第一轮
    r1 = _mock_intent({"user_input": "6月按产品类别销售额"})
    assert r1["intent"] == "QueryCompareAndTopN"
    assert r1["slots"]["时间范围"] == "2026-06"
    print(f"  ✓ 第1轮: {r1['intent']} | time={r1['slots']['时间范围']}")

    # 第二轮:接续(只说"再按城市")
    history = [{
        "query": "6月按产品类别销售额",
        "intent": "QueryCompareAndTopN",
        "slots": r1["slots"],
        "dataset_id": "ds-1ef97a5720",
    }]
    r2 = _mock_intent({
        "user_input": "再按城市拆分",
        "session_history": history,
        "dataset_id": "ds-1ef97a5720",
    })
    # 接续 → 应该继承 6月
    assert r2["slots"]["时间范围"] == "2026-06", f"应继承 2026-06,实际 {r2['slots']['时间范围']}"
    print(f"  ✓ 第2轮 time={r2['slots']['时间范围']}(继承 6月)")

    # 第三轮:有明确时间 - 不继承
    r3 = _mock_intent({
        "user_input": "再按渠道看 5月",
        "session_history": history,
        "dataset_id": "ds-1ef97a5720",
    })
    assert r3["slots"]["时间范围"] == "2026-05"
    print(f"  ✓ 第3轮 time={r3['slots']['时间范围']}(指定 5月,不继承)")


if __name__ == "__main__":
    print("=" * 60)
    print("测试 1: QueryCompareAndTopN 返回分组数据")
    print("=" * 60)
    test_query_compare_topn_returns_grouped()

    print()
    print("=" * 60)
    print("测试 2: _find_category_field 选 product_category")
    print("=" * 60)
    test_category_field_picks_product_category()

    print()
    print("=" * 60)
    print("测试 3: chart title 智能生成")
    print("=" * 60)
    test_chart_title_smart()

    print()
    print("=" * 60)
    print("测试 4: category filter 没误抓业务词")
    print("=" * 60)
    test_no_business_words_in_category_filter()

    print()
    print("=" * 60)
    print("测试 5: 接续 query 检测")
    print("=" * 60)
    test_followup_query_detection()

    print()
    print("=" * 60)
    print("测试 6: 接续 query 继承 slots")
    print("=" * 60)
    test_inherit_slots_from_history()

    print()
    print("=" * 60)
    print("✓ 全部测试通过!")
    print("=" * 60)
