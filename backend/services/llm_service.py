"""Mock LLM 服务 - 改进版:动态识别用户上传的 Schema

特性:
1. 动态读取上传数据集的实际字段,不再硬编码零售样本字段
2. 增强 intent 识别:用户数 / 数量 / 购买 / 配置 等
3. 智能解析时间范围:5月份 / 自然月 / 上季度 / 2026-05-15
4. 智能提取筛选条件:device_config = 'mac pro 32G 1T'
5. 生成 SQL 时使用实际字段名 + COUNT(DISTINCT) 等聚合

术语表(用户友好映射):
- GMV  =  Gross Merchandise Value  =  商品总销售额(成交总额,不含退款)
- amount  =  销售额(同 GMV)
- profit  =  利润
- 贡献度  =  占比(归因分析用)
- 维度  =  类目/分组字段
"""
from __future__ import annotations
import asyncio
import re
from datetime import datetime, timedelta

from config import LLM_MOCK_DELAY_MS
from models.schemas import IntentName


async def mock_call(agent_name: str, user_input: dict) -> dict:
    """统一 Mock LLM 调用入口"""
    await asyncio.sleep(LLM_MOCK_DELAY_MS / 1000.0)

    if agent_name == "intent_agent":
        return _mock_intent(user_input)
    if agent_name == "schema_agent":
        return _mock_schema(user_input)
    if agent_name == "nl2sql_agent":
        return _mock_nl2sql(user_input)
    if agent_name == "storytelling_agent":
        return _mock_storytelling(user_input)
    return {}


# ==================== 多轮对话工具 ====================
def _is_followup_query(text: str) -> bool:
    """检测接续 query - 包含"再/也/还/那/呢/对比"等词,或很短(无时间/无主语)"""
    if not text:
        return False
    text = text.strip()
    # 显式接续词
    followup_keywords = ["再", "也", "还", "那", "呢", "那按", "拆", "对比", "另一个", "按不同"]
    if any(k in text for k in followup_keywords):
        return True
    # 句子很短(< 8 字符)且没有主语 → 多半是接续
    if len(text) < 8 and not any(w in text for w in ["什么", "哪个", "怎样", "怎么"]):
        # 但 "6月销售额" 这种短句不算接续
        if not _parse_time_range(text)["label"]:
            return True
    return False


def _find_recent_query(history: list, target_dataset: str = "") -> dict | None:
    """从历史中找最近一条同 dataset 的查询(继承它的 intent+slots)"""
    for h in history:
        # 每条 history 应包含 intent + slots
        if not h.get("intent"):
            continue
        # dataset 匹配(空就匹配任意)
        if target_dataset and h.get("dataset_id") and h["dataset_id"] != target_dataset:
            continue
        return h
    return None


# ==================== 时间解析工具 ====================
def _parse_time_range(text: str) -> dict:
    """解析自然语言时间范围,返回 {label, start_date, end_date}
    支持: "5月", "5月份", "2026-05", "2026年5月", "上周", "近7天" 等
    """
    from datetime import datetime as _dt

    today = _dt.utcnow().date()
    text = text.strip()

    # ISO 格式: 2026-05 / 2026-05-15 / 2026/05
    m = re.search(r"(\d{4})[-/](\d{1,2})(?:\s*$|[-/]\d{1,2})?", text)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        start = _dt(year, month, 1).date()
        if month == 12:
            end = _dt(year + 1, 1, 1).date()
        else:
            end = _dt(year, month + 1, 1).date()
        return {"label": f"{year}-{month:02d}", "start": start.isoformat(), "end": end.isoformat()}

    # 自然月: 5月份 / 五月 / 2026年5月
    m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月", text)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        start = _dt(year, month, 1).date()
        if month == 12:
            end = _dt(year + 1, 1, 1).date()
        else:
            end = _dt(year, month + 1, 1).date()
        return {"label": f"{year}-{month:02d}", "start": start.isoformat(), "end": end.isoformat()}

    m = re.search(r"(\d{1,2})\s*月份", text)
    if m:
        month = int(m.group(1))
        year = today.year
        start = _dt(year, month, 1).date()
        if month == 12:
            end = _dt(year + 1, 1, 1).date()
        else:
            end = _dt(year, month + 1, 1).date()
        return {"label": f"{year}-{month:02d}", "start": start.isoformat(), "end": end.isoformat()}

    # 数字月: 5月 / 05月
    m = re.search(r"(\d{1,2})\s*月(?![份度])", text)
    if m:
        month = int(m.group(1))
        year = today.year
        start = _dt(year, month, 1).date()
        if month == 12:
            end = _dt(year + 1, 1, 1).date()
        else:
            end = _dt(year, month + 1, 1).date()
        return {"label": f"{year}-{month:02d}", "start": start.isoformat(), "end": end.isoformat()}

    # 相对时间
    if "今天" in text or "今日" in text:
        return {"label": "今天", "start": today.isoformat(), "end": (today + timedelta(days=1)).isoformat()}
    if "昨天" in text:
        return {"label": "昨天", "start": (today - timedelta(days=1)).isoformat(), "end": today.isoformat()}
    if "本周" in text or "这周" in text:
        start = today - timedelta(days=today.weekday())
        return {"label": "本周", "start": start.isoformat(), "end": (today + timedelta(days=1)).isoformat()}
    if "上周" in text:
        end = today - timedelta(days=today.weekday())
        start = end - timedelta(days=7)
        return {"label": "上周", "start": start.isoformat(), "end": end.isoformat()}
    if "本月" in text or "这个月" in text or "当月" in text:
        start = _dt(today.year, today.month, 1).date()
        return {"label": "本月", "start": start.isoformat(), "end": (today + timedelta(days=1)).isoformat()}
    if "上月" in text or "上个月" in text:
        if today.month == 1:
            start = _dt(today.year - 1, 12, 1).date()
            end = _dt(today.year, 1, 1).date()
        else:
            start = _dt(today.year, today.month - 1, 1).date()
            end = _dt(today.year, today.month, 1).date()
        return {"label": "上月", "start": start.isoformat(), "end": end.isoformat()}

    # 近 N 天
    m = re.search(r"近\s*(\d+)\s*([天日周月])", text)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        if unit in ("天", "日"):
            start = today - timedelta(days=n)
            return {"label": f"近 {n} 天", "start": start.isoformat(), "end": (today + timedelta(days=1)).isoformat()}
        if unit == "周":
            start = today - timedelta(weeks=n)
            return {"label": f"近 {n} 周", "start": start.isoformat(), "end": (today + timedelta(days=1)).isoformat()}
        if unit == "月":
            start = today - timedelta(days=n * 30)
            return {"label": f"近 {n} 月", "start": start.isoformat(), "end": (today + timedelta(days=1)).isoformat()}

    return {"label": "全部时间", "start": "", "end": ""}


# ==================== Agent 1: IntentAgent ====================
def _mock_intent(input_data: dict) -> dict:
    """识别意图 + 提取槽位(支持多轮对话接续)"""
    text = input_data.get("user_input", "")
    history = input_data.get("session_history") or []

    # 1. 检测接续词(从上一轮继承)
    is_followup = _is_followup_query(text)
    inherited_slots: dict = {}
    if is_followup and history:
        # 取最近一条同 dataset 的查询继承
        last = _find_recent_query(history, target_dataset=input_data.get("dataset_id", ""))
        if last and last.get("slots"):
            inherited_slots = dict(last.get("slots", {}))

    # 时间范围
    time_range = _parse_time_range(text)
    time_label = time_range["label"] or "最近7天"
    # 趋势查询且没有明确时间范围 → 默认"全部时间"
    if any(k in text for k in ["趋势", "走势", "每日", "按日", "按天"]) and not time_label:
        time_label = "全部时间"

    # 接续 query 没指定时间 → 继承上一轮(以 _parse_time_range 的 start 为准)
    if is_followup and not time_range.get("start") and inherited_slots.get("时间范围"):
        time_label = inherited_slots["时间范围"]

    # 指标识别
    # 默认 metric = GMV(商品总销售额 / Gross Merchandise Value)
    metric = "GMV"
    if any(k in text for k in ["用户", "客户", "人数", "购买者", "买家"]):
        metric = "用户数"
    elif any(k in text for k in ["数量", "多少个", "几个", "有多少"]):
        if any(k in text for k in ["用户", "客户", "购买者", "买家"]):
            metric = "用户数"
        elif any(k in text for k in ["订单", "单"]):
            metric = "订单量"
        elif any(k in text for k in ["SKU", "商品", "产品", "品类"]):
            metric = "商品数"
        else:
            metric = "数量"
    elif any(k in text for k in ["GMV", "gmv", "销售额", "成交额", "营收"]):
        metric = "GMV"
    # 接续 query 没指定指标 → 继承上一轮
    if metric == "GMV" and is_followup and inherited_slots.get("指标"):
        # 但跳过"用户数"等特殊指标
        if inherited_slots["指标"] not in ("GMV", "数量"):
            metric = inherited_slots["指标"]
    elif any(k in text for k in ["订单", "单量", "销量"]):
        metric = "订单量"
    elif any(k in text for k in ["转化率", "转化"]):
        metric = "转化率"
    elif any(k in text for k in ["客单价", "客单"]):
        metric = "客单价"
    elif any(k in text for k in ["库存"]):
        metric = "库存"
    elif any(k in text for k in ["毛利", "利润率"]):
        metric = "毛利率"

    # 意图分类
    intent = "QueryBasicMetrics"
    confidence = 0.85
    alternatives = []
    slots = {"指标": metric, "时间范围": time_label, "filters": []}

    if any(k in text for k in ["为什么", "原因", "怎么掉", "怎么涨", "归因", "因素", "分析"]):
        intent = "AttributeAnalysis"
        confidence = 0.92
    if any(k in text for k in ["按", "分", "组", "维度", "top", "TOP", "排名", "前几", "前10", "最", "对比", "环比", "同比", "卖得", "畅销", "热卖", "最好", "前3", "前5", "前2", "前1", "各类", "各品类", "各种", "分门", "分组看", "类别分析", "品类分析", "看出", "来看", "拆", "拆解", "类别销售额", "品类销售额", "类别销量", "品类销量", "类别利润", "品类利润", "类别数量", "品类数量", "销售额", "销量", "利润", "数量", "GMV", "金额"]):
        intent = "QueryCompareAndTopN"
        confidence = 0.88
        # 智能解析 TOP_N:从"前3"/"前5"/"TOP 10"等
        m = re.search(r"(?:前|TOP|top|Top)\s*(\d+)", text)
        top_n_val = int(m.group(1)) if m else 10
        slots = {"指标": metric, "时间范围": time_label, "TOP_N": top_n_val, "filters": []}
    elif any(k in text for k in ["异常", "预警", "阈值", "超过", "低于", "不足"]):
        intent = "ThresholdAlert"
        confidence = 0.85
    elif any(k in text for k in ["解读", "解释", "说明", "怎么样", "分析一下"]):
        intent = "SmartInterpretation"
        confidence = 0.82
    elif metric == "用户数":
        # 用户数查询是 Distinct Count,标注为新的 QueryUserCount
        intent = "QueryUserCount"
        confidence = 0.90
        alternatives = ["QueryBasicMetrics"]

    # 趋势分析优先级最高(检查明确的时间序列词)
    if any(k in text for k in ["趋势", "走势", "每日", "按日", "按天", "天级", "时间序列", "日均", "每日新增", "随时间"]):
        intent = "QueryTrend"
        confidence = 0.93
        if "用户" in text or "人数" in text:
            metric = "用户数"
        # 只有用户**没明确**说 GMV/销售额,才用"数量"作为默认
        # (用"原句"判断,不用 metric 判断 — metric 已经被前面的 _detect_metric 设置过)
        elif not any(k in text for k in ["GMV", "gmv", "销售额", "成交额", "营收", "amount"]):
            metric = "数量"

    # 提取筛选条件(简单正则)
    filters = _extract_filters(text)
    filters = _extract_filters(text)

    # 接续 query 继承上一轮的 filters + intent
    inherited_intent = inherited_slots.get("intent") if is_followup else None
    inherited_filters = inherited_slots.get("filters", []) if is_followup else []
    if is_followup and inherited_filters and not filters:
        # 用户没指定新 filter 时,继承上一轮
        filters = list(inherited_filters)
    if is_followup and inherited_intent:
        # 智能继承 intent:如果当前 query 没明确新 intent,沿用
        if intent == "QueryBasicMetrics" and inherited_intent in (
            "QueryCompareAndTopN", "QueryUserCount", "QueryTrend"
        ):
            intent = inherited_intent
            confidence = 0.85

    slots = {
        "指标": metric,
        "时间范围": time_label,
        "filters": filters,
    }
    if intent == "QueryCompareAndTopN":
        # 智能解析 TOP_N:从"前3"/"前5"/"TOP 10"等
        m = re.search(r"(?:前|TOP|top|Top)\s*(\d+)", text)
        slots["TOP_N"] = int(m.group(1)) if m else 10

    return {
        "intent": intent,
        "confidence": confidence,
        "slots": slots,
        "alternatives": alternatives,
    }


def _extract_filters(text: str) -> list:
    """从自然语言中提取筛选条件

    优先级(从最具体到最宽松):
    1. 状态词:已支付/取消/paid → status
    2. 有效/无效 → is_valid
    3. "配置为 X" → device_config
    4. "X 每日趋势" → device_config(去掉时间/动词/停用词)
    5. "购买 X" → device_config
    6. "类别 X" / "品类 X" → category
    7. "渠道 X" → channel
    8. "地区 X" → region
    """
    filters = []

    # ===== 1. 状态:已支付 / 取消 / paid (强匹配,最早处理) =====
    m = re.search(r"(?:状态[为是]?|)\s*(已支付|已付款|paid|取消|未付款|退款|已取消)", text, re.IGNORECASE)
    if m:
        filters.append({"field": "status", "op": "=", "value": m.group(1).strip()})
        # 不 return,允许同时有其他 filter(例如 device_config)

    # ===== 2. 有效/无效 → is_valid (中匹配) =====
    if "无效" in text or "非有效" in text or "不有效" in text:
        filters.append({"field": "is_valid", "op": "=", "value": 0})
    elif "有效" in text:
        # 排除 "无效" 已经处理过的情况
        filters.append({"field": "is_valid", "op": "=", "value": 1})

    # ===== 3. "配置为 X" / "配置是 X" (强匹配) =====
    m = re.search(r"配置[为是]\s*(.+?)(?=\s*[，。,]|\s*的\s*[一-龥]|\s*$)", text)
    if m:
        val = m.group(1).strip()
        # 去掉"的有效用户"等尾巴
        val = re.sub(r"\s*(的(?:有效|无效)?(?:用户|客户|买家|订单|数据|记录))$", "", val)
        if val and val not in ("有效", "无效"):
            filters.append({"field": "device_config", "op": "=", "value": val})
            return filters

    # ===== 4. "X 每日购买趋势" / "X 每天购买" =====
    m = re.search(r"^(.+?)\s*(?:每[日天]|按[日天]|天级|日均|每日新增|随时间)", text)
    if m:
        val = m.group(1).strip()
        # 循环剥离开头的停用词(直到不再匹配)
        for _ in range(3):  # 最多剥 3 次
            new_val = re.sub(
                r"^(统计|看看|展示|分析|显示|查|给我|我想知道|近\d+天|第\d+季度|上周|本周|本月|上月|今天|昨天"
                r"|5月份?|4月份?|3月份?|2月份?|1月份?|6月份?|7月份?|8月份?|9月份?|10月份?|11月份?|12月份?"
                r"|5月|4月|3月|2月|1月|6月|7月|8月|9月|10月|11月|12月"
                r"|近\d+个月|2026年\d+月|2025年\d+月"
                r")\s*", "", val
            )
            new_val = re.sub(r"^购买\s*", "", new_val)
            new_val = re.sub(r"^配置[为是]?\s*", "", new_val)
            if new_val == val:
                break
            val = new_val
        # 去掉结尾的停用词(包括"有效"和"无效",已被 is_valid 处理)
        val = re.sub(r"\s*(购买|销量|销售|订单|配置|用户|客户|买家|的购买|的销量|的订单|的数据|的配置|的有效用户|的无效用户|的有效|的无效|的买家|的客户的?)$", "", val)
        val = re.sub(r"\s*的\s*$", "", val)
        # 如果剥完后只剩状态词,跳过
        if val and val not in ("有效", "无效", "购买", "配置", "用户", "客户"):
            filters.append({"field": "device_config", "op": "=", "value": val.strip()})
            return filters

    # ===== 5. "购买 X" / "买了 X" - 中段 =====
    m = re.search(r"(?:购买|买了|买)\s*(.+?)(?=\s*的|\s*[,。]|\s*$)", text)
    if m:
        val = m.group(1).strip()
        val = re.sub(r"^配置[为是]?\s*", "", val)
        # 去掉尾巴
        val = re.sub(r"\s*(的(?:有效|无效)?(?:用户|客户|买家|订单|数据|记录))$", "", val)
        # 排除纯状态词
        if val and not re.match(r"^(数量|人数|次数|多少|几次|有效|无效)$", val):
            filters.append({"field": "device_config", "op": "=", "value": val})
            return filters

    # ===== 6. "类别 X" / "品类 X" =====
    # 用 negative lookbehind 防止跨词抽取(例如 "产品类别销售额" 中的"类别"前面是"品",不抽)
    # 排除业务词 - 避免把 "销售额"/"销量" 等当作 category 值
    _BUSINESS_TERMS = {"销售额", "销量", "金额", "订单量", "数量", "GMV", "营收", "利润", "利润额"}
    m = re.search(r"(?<![一-龥])(?:类别|品类[是为]?)\s*(.+?)(?=\s*的|\s*[,。]|\s*$)", text)
    if m:
        val = m.group(1).strip()
        # 多道防线:
        # 1. 不在业务词黑名单
        # 2. 不以业务词结尾(防止 "别销售额" 这种)
        # 3. 不以 "X" 等通用词结尾
        _BAD_TAILS = {"销售额", "销量", "金额", "GMV", "营收", "利润", "订单量", "数量"}
        is_bad = (
            val in _BUSINESS_TERMS
            or any(val.endswith(t) for t in _BAD_TAILS)
            or len(val) > 12
            or val.startswith(("按", "上", "下", "第", "总", "总"))
        )
        if val and not is_bad and len(val) >= 2:
            filters.append({"field": "category", "op": "=", "value": val})
            return filters

    # ===== 7. 渠道 =====
    m = re.search(r"渠道[是为]?\s*(.+?)(?=\s*的|\s*[,。]|\s*$)", text)
    if m:
        filters.append({"field": "channel", "op": "=", "value": m.group(1).strip()})
        return filters

    # ===== 8. 地区 =====
    m = re.search(r"地区[是为]?\s*(.+?)(?=\s*的|\s*[,。]|\s*$)", text)
    if m:
        filters.append({"field": "region", "op": "=", "value": m.group(1).strip()})
        return filters

    return filters


# ==================== Agent 2: SchemaAgent ====================
def _mock_schema(input_data: dict) -> dict:
    """根据实际数据集 Schema 动态映射"""
    slots = input_data.get("slots", {})
    metadata = input_data.get("data_source_metadata", [])
    glossary = input_data.get("business_glossary", {})

    if not metadata:
        return {
            "tables": [],
            "fields": [],
            "filters": [],
            "joins": [],
            "unmapped_slots": list(slots.keys()),
            "confidence": 0.0,
            "error": "未找到数据集",
        }

    # 默认使用第一张表
    table = metadata[0]
    fields = [f["name"] for f in table.get("fields", [])]
    field_types = {f["name"]: f.get("type", "") for f in table.get("fields", [])}

    intent = input_data.get("intent", "")
    user_filters = slots.get("filters", [])

    # 时间字段
    time_range = _parse_time_range(slots.get("时间范围", ""))
    time_field = _detect_time_field(field_types)

    base_filters = []
    unmapped = []

    # 时间范围筛选
    if time_range["start"] and time_field:
        base_filters.append({"field": time_field, "op": ">=", "value": time_range["start"]})
        if time_range["end"]:
            base_filters.append({"field": time_field, "op": "<", "value": time_range["end"]})

    # 用户自定义筛选
    for f in user_filters:
        if f["field"] in fields:
            base_filters.append(f)
        else:
            # 模糊匹配字段名
            fuzzy = next((fn for fn in fields if f["field"].lower() in fn.lower() or fn.lower() in f["field"].lower()), None)
            if fuzzy:
                base_filters.append({**f, "field": fuzzy})
            else:
                unmapped.append(f["field"])

    # 业务术语
    metric = slots.get("指标", "")
    if metric in glossary:
        base_filters.append({"field": metric, "op": "=", "value": glossary[metric]})

    # 找出度量字段
    measure_field = _detect_measure_field(fields, field_types)

    return {
        "tables": [table["name"]],
        "fields": fields,
        "measure_field": measure_field,
        "time_field": time_field,
        "filters": base_filters,
        "joins": [],
        "unmapped_slots": unmapped,
        "confidence": 0.9 if base_filters else 0.7,
    }


def _detect_time_field(field_types: dict) -> str:
    """检测时间字段 - 优先匹配 datetime 类型,再匹配字段名"""
    # 优先级 1: 字段类型含 datetime/timestamp
    for name, typ in field_types.items():
        if any(k in typ.lower() for k in ["datetime", "timestamp", "date64"]):
            return name
    # 优先级 2: 字段名含时间关键字(避免误匹配 order_id)
    for name in field_types:
        nl = name.lower()
        if any(k in nl for k in ["buy_time", "create_time", "update_time", "时间", "日期", "date"]):
            return name
        if nl.endswith("_time") or nl.endswith("_date"):
            return name
    # 优先级 3: 包含 "time" 关键字(但不包含 "id")
    for name in field_types:
        if "time" in name.lower() and "id" not in name.lower():
            return name
    return ""


def _detect_measure_field(fields: list, field_types: dict) -> str:
    """检测可度量的数值字段"""
    for f in fields:
        if f in ("amount", "count", "total", "gmv", "price", "金额", "数量", "sum"):
            return f
    # 找第一个 numeric 字段
    for f, t in field_types.items():
        if any(k in t.lower() for k in ["int", "float", "number"]):
            return f
    return fields[0] if fields else ""


def _detect_money_field(fields: list) -> str:
    """检测金额类字段"""
    money_keywords = ["amount", "price", "gmv", "total", "sum", "金额", "价格", "销售额", "revenue"]
    for f in fields:
        fl = f.lower()
        for kw in money_keywords:
            if kw in fl or fl in kw:
                return f
    return ""


# ==================== Agent 3: NL2SQLAgent ====================
def _mock_nl2sql(input_data: dict) -> dict:
    """生成 SQL - 使用实际 schema"""
    intent = input_data.get("intent", "QueryBasicMetrics")
    slots = input_data.get("slots", {})
    mapped = input_data.get("mapped_query", {})
    user_input = input_data.get("user_input", "")

    # SQLite 中数据总是存在 `orders` 表(由 dataset_loader.py 固定)
    # schema_agent 返回的是「逻辑表名」(数据集名),这里需要转成物理表名
    table = "orders"
    filters = mapped.get("filters", [])
    measure_field = mapped.get("measure_field", "amount")
    time_field = mapped.get("time_field", "order_date")

    # 构造 WHERE 子句
    where_parts = []
    for f in filters:
        field = f"`{f['field']}`"
        val = f["value"]
        if isinstance(val, str):
            val_safe = val.replace("'", "''")
            where_parts.append(f"{field} {f['op']} '{val_safe}'")
        else:
            where_parts.append(f"{field} {f['op']} {val}")
    where = " AND ".join(where_parts) if where_parts else "1=1"

    time_range = slots.get("时间范围", "最近7天")
    metric = slots.get("指标", "数量")
    top_n = slots.get("TOP_N", 10)

    # 取出 fields 列表(供 _detect_money_field 等使用)
    fields = mapped.get("fields", [])

    # 根据意图生成 SQL
    if intent == "QueryUserCount":
        # 用户数 / Distinct Count 用户
        sql = f"SELECT COUNT(DISTINCT `user_id`) AS 用户数 FROM `{table}` WHERE {where} LIMIT 1000"
        explanation = f"统计指定条件下不同用户数,时间范围 {time_range}"

    elif intent == "QueryTrend":
        # 时间序列趋势 - 按天聚合(SQLite date() 截断到日)
        # 趋势查询每天一行,数据量小,不需要 LIMIT 1000
        if "user" in metric or "用户" in metric:
            # 用户去重的趋势(每个 user 在该日只算一次)
            sql = f"""SELECT date(`{time_field}`) AS 日期, COUNT(DISTINCT `user_id`) AS {metric}
FROM `{table}` WHERE {where}
GROUP BY date(`{time_field}`)
ORDER BY 日期"""
        elif metric in ("GMV", "amount", "销售额", "金额"):
            # 销售额类 — 用 SUM(measure_field)
            sql = f"""SELECT date(`{time_field}`) AS 日期, SUM(`{measure_field}`) AS {metric}
FROM `{table}` WHERE {where}
GROUP BY date(`{time_field}`)
ORDER BY 日期"""
        else:
            # 数量趋势(订单数)
            sql = f"""SELECT date(`{time_field}`) AS 日期, COUNT(*) AS {metric}
FROM `{table}` WHERE {where}
GROUP BY date(`{time_field}`)
ORDER BY 日期"""
        explanation = f"按天统计 {metric} 趋势,时间范围 {time_range}"

    elif intent == "QueryBasicMetrics":
        # 单值聚合:根据 metric 选择合适字段和聚合函数
        if "user" in metric or "用户" in metric:
            agg_sql = f"COUNT(DISTINCT `{measure_field}`)"
        elif metric in ("GMV", "amount", "销售额", "金额", "营收"):
            # 找金额类字段
            money_field = _detect_money_field(fields)
            if money_field:
                agg_sql = f"SUM(`{money_field}`)"
            else:
                # 没有金额字段 → 降级为订单数
                agg_sql = f"COUNT(*)"
        else:
            agg_sql = f"COUNT(*)"
        sql = f"SELECT {agg_sql} AS {metric} FROM `{table}` WHERE {where} LIMIT 1000"
        explanation = f"聚合 {metric},时间范围 {time_range}"

    elif intent == "QueryCompareAndTopN":
        # 智能选择聚合函数:用户数 → COUNT(DISTINCT),GMV → SUM(amount) 否则 COUNT(*)
        if "user" in metric or "用户" in metric:
            agg_expr = f"COUNT(DISTINCT `{measure_field}`)"
        elif metric in ("GMV", "amount", "销售额", "金额", "营收"):
            money_field = _detect_money_field(fields)
            if money_field:
                agg_expr = f"SUM(`{money_field}`)"
            else:
                agg_expr = f"COUNT(*)"  # 无 amount 字段 → 降级为订单数
        else:
            agg_expr = f"COUNT(*)"

        # 列名友好化(用真实类目字段名替代'维度'/'GMV'字面词)
        cat_field = _find_category_field(mapped)
        # 类目字段名转中文友好
        cat_field_friendly = {
            "product_category": "产品类别",
            "category": "类别",
            "device_config": "设备",
            "customer_city": "城市",
            "region": "地区",
            "channel": "渠道",
            "品类": "品类",
        }.get(cat_field.lower() if isinstance(cat_field, str) else "", cat_field)

        # 指标字段名友好化
        metric_friendly = {
            "GMV": "销售额",
            "amount": "销售额",
            "sales_amount": "销售额",
            "profit": "利润",
            "用户数": "用户数",
        }.get(metric, metric)

        if "TOP" in user_input.upper() or top_n:
            sql = f"""SELECT `{cat_field}` AS `{cat_field_friendly}`, {agg_expr} AS `{metric_friendly}`
FROM `{table}` WHERE {where}
GROUP BY `{cat_field}` ORDER BY {metric_friendly} DESC LIMIT {top_n}"""
            explanation = f"按 {cat_field} Top {top_n} 排序"
        else:
            sql = f"""SELECT `{cat_field}` AS `{cat_field_friendly}`, {agg_expr} AS `{metric_friendly}`
FROM `{table}` WHERE {where}
GROUP BY `{cat_field}` ORDER BY `{metric_friendly}` DESC LIMIT {top_n}"""
            explanation = f"按 {cat_field} 排序"

    elif intent == "ThresholdAlert":
        if "user" in metric or "用户" in metric:
            agg_expr = f"COUNT(DISTINCT `{measure_field}`)"
        elif metric in ("GMV", "amount", "销售额", "金额", "营收"):
            money_field = _detect_money_field(fields)
            if money_field:
                agg_expr = f"SUM(`{money_field}`)"
            else:
                agg_expr = f"COUNT(*)"
        else:
            agg_expr = f"COUNT(*)"

        cat_field = _find_category_field(mapped)
        cat_field_friendly = {
            "product_category": "产品类别", "category": "类别", "device_config": "设备",
            "customer_city": "城市", "region": "地区", "channel": "渠道",
        }.get(cat_field.lower() if isinstance(cat_field, str) else "", cat_field)
        metric_friendly = {
            "GMV": "销售额", "amount": "销售额", "profit": "利润",
        }.get(metric, metric)
        sql = f"""SELECT `{cat_field}` AS `{cat_field_friendly}`, {agg_expr} AS `{metric_friendly}`
FROM `{table}` WHERE {where}
GROUP BY `{cat_field}` HAVING `{metric_friendly}` < 1000
ORDER BY `{metric_friendly}` ASC LIMIT 50"""
        explanation = f"阈值预警查询,时间范围 {time_range}"

    elif intent == "AttributeAnalysis":
        if "user" in metric or "用户" in metric:
            agg_expr = f"COUNT(DISTINCT `{measure_field}`)"
        elif metric in ("GMV", "amount", "销售额", "金额", "营收"):
            money_field = _detect_money_field(fields)
            if money_field:
                agg_expr = f"SUM(`{money_field}`)"
            else:
                agg_expr = f"COUNT(*)"
        else:
            agg_expr = f"COUNT(*)"

        cat_field = _find_category_field(mapped)
        cat_field_friendly = {
            "product_category": "产品类别", "category": "类别", "device_config": "设备",
            "customer_city": "城市", "region": "地区", "channel": "渠道",
        }.get(cat_field.lower() if isinstance(cat_field, str) else "", cat_field)
        metric_friendly = {
            "GMV": "销售额", "amount": "销售额", "profit": "利润",
        }.get(metric, metric)
        sql = f"""SELECT `{cat_field}` AS `{cat_field_friendly}`, {agg_expr} AS `{metric_friendly}`,
       {agg_expr} * 1.0 / SUM({agg_expr}) OVER () AS 贡献度
FROM `{table}` WHERE {where}
GROUP BY `{cat_field}` ORDER BY 贡献度 DESC LIMIT 10"""
        explanation = f"归因分析,按 {cat_field} 拆解,时间范围 {time_range}"

    else:  # SmartInterpretation
        if "user" in metric or "用户" in metric:
            agg_expr = f"COUNT(DISTINCT `{measure_field}`)"
        elif metric in ("GMV", "amount", "销售额", "金额", "营收"):
            money_field = _detect_money_field(fields)
            if money_field:
                agg_expr = f"SUM(`{money_field}`)"
            else:
                agg_expr = f"COUNT(*)"
        else:
            agg_expr = f"COUNT(*)"

        sql = f"""SELECT `{time_field}` AS 日期, {agg_expr} AS {metric}
FROM `{table}` WHERE {where}
GROUP BY `{time_field}` ORDER BY 日期 LIMIT 30"""
        explanation = f"趋势分析,时间范围 {time_range}"

    return {
        "sql": sql,
        "params": {},
        "explanation": explanation,
        "confidence": 0.93,
        "is_executable": True,
        "validation_errors": [],
    }


def _find_category_field(mapped: dict) -> str:
    """从 schema 中找分类字段 - 优先选择产品/类别/品类相关的字段"""
    fields = mapped.get("fields", [])
    # 尝试从 metadata 中获取类型
    metadata = mapped.get("data_source_metadata", [])
    field_types = {}
    if metadata and isinstance(metadata[0], dict):
        for f in metadata[0].get("fields", []):
            field_types[f["name"]] = f.get("type", "")

    # 1. 精确匹配:category, 类型, 种类
    for name in ["category", "类型", "种类"]:
        if name in fields:
            return name

    # 2. 含特定关键词的字段(如 product_category, item_type, etc)
    for f in fields:
        if any(k in f.lower() for k in ["category", "type", "kind"]):
            return f

    # 3. 业务字段(优先级)
    for name in ["产品类别", "品类", "类别"]:
        if name in fields:
            return name

    # 4. 区域/渠道/位置字段
    for name in ["region", "地区"]:
        if name in fields:
            return name
    for name in ["channel", "渠道"]:
        if name in fields:
            return name

    # 5. 设备/配置字段
    for name in ["device_config", "配置"]:
        if name in fields:
            return name

    # 6. 找第一个非数值、非时间、非 ID 字段
    skip = {"user_id", "order_id", "is_valid", "etl_extract_time",
            "buy_time", "order_date", "id", "_id", "uuid"}
    for f in fields:
        if f.lower() in skip or f.endswith("_id") or f.endswith("id"):
            continue
        t = field_types.get(f, "")
        if "int" in t.lower() or "float" in t.lower() or "date" in t.lower() or "time" in t.lower():
            continue
        return f

    # 最后回退
    if fields:
        return fields[0]
    return "category"


# ==================== Agent 4: StorytellingAgent ====================
def _mock_storytelling(input_data: dict) -> dict:
    """讲故事 - 修复版,兼容用户数 / 趋势查询"""
    from config import REPORT_TEMPLATE

    full_result = input_data.get("full_result", {})
    sql_result = full_result.get("sql_result", {})
    rows = sql_result.get("rows", [])
    intent = full_result.get("intent", "QueryBasicMetrics")
    slots = full_result.get("slots", {})
    metric = slots.get("指标", "GMV")
    time_range = slots.get("时间范围", "最近7天")

    interpretation = _interpret_rows(rows, intent, metric, time_range)
    observations = _gen_observations(rows, intent, metric)
    from tools.generate_next_steps import generate_next_steps as _ns

    ns_result = _ns(
        story_context={"rows": rows, "intent": intent},
        intent=intent,
        slots=slots,
    )
    next_steps = ns_result.get("next_steps", [])
    followups = ns_result.get("recommended_followups", [])

    copy_text = _gen_copy_text(metric, time_range, interpretation, observations)

    # 标题适配
    if intent == "QueryUserCount":
        title = f"用户数 分析报告 ({time_range})"
    elif intent == "QueryTrend":
        # 从 user_input 提取主体(配置 / 类目等)
        subject = _extract_subject(input_data)
        if subject:
            title = f"{subject} 每日{metric}趋势"
        else:
            title = f"每日{metric}趋势 ({time_range})"
    else:
        title = f"{metric} 分析报告 ({time_range})"

    # 趋势图:把 SQL 结果渲染为 line chart
    charts = []
    if intent == "QueryTrend" and rows:
        chart = _build_trend_chart(rows, metric, time_range)
        if chart.get("success"):
            charts.append(chart)
    elif rows and len(rows) > 1:
        # 多行结果自动适配
        from tools.render_chart import render_chart
        ch = render_chart(data=rows, title=f"{metric} 分析 ({time_range})")
        if ch.get("success"):
            charts.append(ch)

    return {
        "title": title,
        "summary": interpretation[:1] if isinstance(interpretation, list) else interpretation,
        "sections": REPORT_TEMPLATE["sections"],
        "observations": observations,
        "next_steps": next_steps,
        "recommended_followups": followups,
        "copy_insight_text": copy_text,
        "confidence_overall": 0.85,
        "charts": charts,
    }


def _extract_subject(input_data: dict) -> str:
    """从 user_input 中提取主体(如 mac pro 32G 1T)"""
    full_result = input_data.get("full_result", {})
    slots = full_result.get("slots", {})
    filters = slots.get("filters", [])
    for f in filters:
        if f.get("field") in ("device_config", "category", "channel", "region"):
            return f.get("value", "")
    return ""


def _build_trend_chart(rows: list[dict], metric: str, time_range: str) -> dict:
    """把 SQL 时间序列结果渲染为折线图"""
    if not rows:
        return {"success": False, "error": "无数据"}
    first = rows[0]
    keys = list(first.keys())
    if len(keys) < 2:
        return {"success": False, "error": "字段不足"}

    x_field = keys[0]  # "日期"
    y_field = keys[1]  # 数值字段

    # 日期格式化为 "M/D" 风格
    x_data = []
    for r in rows:
        v = r.get(x_field, "")
        if hasattr(v, "strftime"):
            v = v.strftime("%m/%d").lstrip("0").replace("/0", "/")
        else:
            s = str(v)
            # "2026-05-05" → "5/5"
            if len(s) == 10 and s[4] == "-":
                m = int(s[5:7])
                d = int(s[8:10])
                v = f"{m}/{d}"
        x_data.append(v)

    # 清理标题:time_range 如果是整个用户输入(没有解析出时间),则不显示
    if time_range and len(time_range) > 12:
        # 时间范围太长了,可能不是真时间,简化标题
        title_text = f"{metric} 每日趋势"
    elif time_range and time_range != "全部时间":
        title_text = f"{metric} 每日趋势 ({time_range})"
    else:
        title_text = f"{metric} 每日趋势"

    return {
        "success": True,
        "chart_type": "line",
        "config": {
            "title": {"text": title_text, "left": "center", "textStyle": {"fontSize": 14}},
            "tooltip": {"trigger": "axis"},
            "grid": {"left": "5%", "right": "5%", "bottom": "10%", "containLabel": True},
            "xAxis": {"type": "category", "data": x_data, "axisLabel": {"rotate": 0}},
            "yAxis": {"type": "value"},
            "series": [{
                "name": y_field,
                "type": "line",
                "data": [r.get(y_field, 0) for r in rows],
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 8,
                "lineStyle": {"width": 3, "color": "#5b6cff"},
                "itemStyle": {"color": "#5b6cff"},
                "areaStyle": {"color": "rgba(91, 108, 255, 0.1)"},
            }],
        },
    }


def _interpret_rows(rows: list[dict], intent: str, metric: str, time_range: str) -> list:
    """智能解读结果"""
    if not rows:
        return [f"{time_range}暂无 {metric} 相关数据,请检查查询条件或时间范围。"]

    if len(rows) == 1:
        val = list(rows[0].values())[0] if rows[0] else 0
        if intent == "QueryUserCount":
            return [
                f"{time_range}{metric} 为 {val:,.0f} 人",
                "数据来源于当前上传的数据集",
                "建议结合同期对比进一步分析趋势",
            ]
        return [
            f"{time_range}{metric} 总额为 {val:,.0f}",
            "数据来源于当前上传的数据集",
            "建议结合同期对比进一步分析趋势",
        ]

    numeric_key = next((k for k, v in rows[0].items() if isinstance(v, (int, float))), None)
    if not numeric_key:
        return ["数据已展示,可点击下方按钮分享或复制"]

    sorted_rows = sorted(rows, key=lambda r: r.get(numeric_key, 0), reverse=True)
    top = sorted_rows[0]
    bottom = sorted_rows[-1]
    total = sum(r.get(numeric_key, 0) for r in rows)

    return [
        f"{time_range}{metric} 总额 {total:,.0f},共 {len(rows)} 个分组",
        f"最高的是 {top.get(list(top.keys())[0], '')}({top.get(numeric_key, 0):,.0f}),占比 {top.get(numeric_key, 0)/total*100:.1f}%" if total else f"最高的是 {top.get(list(top.keys())[0], '')}({top.get(numeric_key, 0):,.0f})",
        f"最低的是 {bottom.get(list(bottom.keys())[0], '')}({bottom.get(numeric_key, 0):,.0f})",
        f"整体分布呈现头部集中特征,建议关注头部贡献与尾部异常",
    ]


def _gen_observations(rows: list[dict], intent: str, metric: str) -> list:
    """观察点"""
    obs = []
    if not rows:
        return [{"text": "暂无数据,建议检查数据集或时间范围", "severity": "warning"}]

    if intent == "QueryUserCount":
        if len(rows) == 1:
            val = list(rows[0].values())[0] if rows[0] else 0
            obs.append({"text": f"指定条件下共有 {val:,.0f} 位独立用户", "severity": "info"})
        return obs or [{"text": f"用户数查询已识别,共 {len(rows)} 条结果", "severity": "info"}]

    numeric_key = next((k for k, v in rows[0].items() if isinstance(v, (int, float))), None)
    if numeric_key and len(rows) >= 2:
        sorted_rows = sorted(rows, key=lambda r: r.get(numeric_key, 0), reverse=True)
        top = sorted_rows[0]
        cat_key = next((k for k in top if k != numeric_key), None)
        if cat_key:
            obs.append({"text": f"{top.get(cat_key, '')} 在 {metric} 上表现最佳,值得借鉴其做法", "severity": "success"})
        if len(sorted_rows) > 1:
            bottom = sorted_rows[-1]
            obs.append({"text": f"{bottom.get(cat_key, '')} 表现较弱,建议排查根因", "severity": "warning"})

    if intent == "AttributeAnalysis":
        obs.append({"text": "归因分析已识别主要驱动维度,可在报告中查看完整链路", "severity": "info"})

    return obs[:5]


def _gen_copy_text(metric: str, time_range: str, interpretation, observations: list) -> str:
    """一键复制文案"""
    lines = [f"📊 {metric} 数据洞察 ({time_range})", ""]
    if isinstance(interpretation, list):
        for s in interpretation[:3]:
            lines.append(f"• {s}")
    if observations:
        lines.append("")
        for o in observations[:3]:
            lines.append(f"• {o['text']}")
    lines.append("")
    lines.append("(由 cocoBI 自动生成)")
    return "\n".join(lines)
