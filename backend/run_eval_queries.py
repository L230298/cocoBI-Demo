"""评测查询脚本 - 跑 10 个查询覆盖 5 个核心意图 + 边界场景
PRD §3.6.2 埋点数据生成

10 个查询清单:
  1. QueryBasicMetrics: "上周 GMV 是多少?"
  2. QueryBasicMetrics: "本月订单量?"
  3. QueryCompareAndTopN: "最近什么卖得好?TOP 10"
  4. QueryCompareAndTopN: "各品类销售额对比"
  5. ThresholdAlert: "库存低于安全线?"
  6. AttributeAnalysis: "为什么这个月订单掉了?"
  7. SmartInterpretation: "解释一下销售数据"
  8. Chitchat: "你能做什么?"
  9. 边界: 空字符串
 10. 边界: 超长 (>500 字符) 故意触发的字符串
"""
from __future__ import annotations
import json
import sys
import time
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

# 10 个评测查询, 覆盖 5 个意图 + 闲聊 + 2 个边界
EVAL_QUERIES = [
    {
        "id": "Q01",
        "label": "基础问数 - 上周 GMV",
        "user_input": "上周 GMV 是多少?",
        "dataset_id": "示例-零售 GMV",
    },
    {
        "id": "Q02",
        "label": "基础问数 - 本月订单量",
        "user_input": "本月订单量?",
        "dataset_id": "示例-零售 GMV",
    },
    {
        "id": "Q03",
        "label": "TopN - 卖得好的 TOP 10",
        "user_input": "最近什么卖得好?TOP 10",
        "dataset_id": "示例-零售 GMV",
    },
    {
        "id": "Q04",
        "label": "对比 - 各品类销售额对比",
        "user_input": "各品类销售额对比",
        "dataset_id": "示例-零售 GMV",
    },
    {
        "id": "Q05",
        "label": "阈值预警 - 库存低于安全线",
        "user_input": "哪些 SKU 库存低于安全线?",
        "dataset_id": "示例-零售 GMV",
    },
    {
        "id": "Q06",
        "label": "归因 - 这个月订单掉了",
        "user_input": "为什么这个月订单掉了?",
        "dataset_id": "示例-零售 GMV",
    },
    {
        "id": "Q07",
        "label": "解读 - 解释销售数据",
        "user_input": "解释一下销售数据",
        "dataset_id": "示例-零售 GMV",
    },
    {
        "id": "Q08",
        "label": "Chitchat - 你能做什么",
        "user_input": "你能做什么?",
        "dataset_id": "示例-零售 GMV",
    },
    {
        "id": "Q09",
        "label": "边界 - 空字符串",
        "user_input": "",
        "dataset_id": "示例-零售 GMV",
    },
    {
        "id": "Q10",
        "label": "边界 - 超长字符串 (>500 字符)",
        "user_input": "请帮我分析一下最近 30 天的整体销售情况、订单数量、转化率、客户活跃度、复购率、客单价、退货率、毛利率、净利率、流量来源、渠道分布、品类分布、地区分布、新老客户占比、热门 SKU TOP 20、滞销 SKU 列表、库存周转天数、客户生命周期价值 LTV、用户分层 RFM、活动效果、优惠券核销率、支付方式占比、客诉率、售后满意度、NPS 评分、竞品对比、价格弹性、需求预测、季节性趋势,把所有这些指标都给我列出来并用图表展示,同时给出解读和策略建议和行动计划,要求覆盖所有维度,生成完整的数据分析报告并下载报告 Word 文档,谢谢",
        "dataset_id": "示例-零售 GMV",
    },
]


def list_datasets() -> list[dict]:
    """列出可用数据集 (取得 dataset_id)"""
    req = urllib.request.Request(f"{BASE_URL}/api/dataset/list")
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        # API 返回 {success, data: [...]} 或直接 [...], 都兼容
        if isinstance(data, dict):
            return data.get("data") or data.get("datasets") or []
        return data


def run_query(user_input: str, dataset_id: str, session_id: str) -> dict:
    """POST /api/chat,消费 NDJSON 流,返回 summary"""
    payload = json.dumps({
        "user_input": user_input,
        "dataset_id": dataset_id,
        "session_id": session_id,
        "conversation_history": [],
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    events = []
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return {"ok": True, "events": events, "event_count": len(events)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}", "events": events}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "events": events}


def main() -> int:
    print("=" * 70)
    print("cocoBI 评测查询脚本")
    print("=" * 70)

    # 1. 健康检查
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=5) as resp:
            print(f"✅ Backend 健康: {resp.read().decode()}")
    except Exception as e:
        print(f"❌ Backend 未运行 ({e}); 请先在另一个终端执行: cd backend && python main.py")
        return 1

    # 2. 解析 dataset_id
    print("\n[1/3] 获取数据集列表...")
    datasets = list_datasets()
    if not datasets:
        print("❌ 没有可用数据集")
        return 2
    # 优先用 '示例-零售 GMV'
    target = None
    for ds in datasets:
        if "示例" in ds.get("name", "") and "GMV" in ds.get("name", ""):
            target = ds
            break
    if not target:
        target = datasets[0]
    real_dataset_id = target["dataset_id"]
    print(f"  使用数据集: {target['name']} ({real_dataset_id}, {target.get('row_count')} 行)")

    # 3. 运行 10 个查询
    print(f"\n[2/3] 运行 {len(EVAL_QUERIES)} 个评测查询...")
    print("-" * 70)
    summary = []
    for i, q in enumerate(EVAL_QUERIES, 1):
        session_id = f"eval-{q['id']}"
        print(f"\n[{i:2d}/10] {q['id']} - {q['label']}")
        print(f"  输入: {q['user_input'][:80]}{'...' if len(q['user_input']) > 80 else ''}")
        t0 = time.time()
        result = run_query(q["user_input"], real_dataset_id, session_id)
        elapsed = time.time() - t0

        ok = result["ok"]
        events = result["events"]
        event_types = [e.get("event") for e in events]

        # 提取 intent
        intent_data = next((e["data"] for e in events if e.get("event") == "intent"), None)
        intent_name = intent_data.get("intent", "?") if intent_data else "?"
        confidence = intent_data.get("confidence", 0) if intent_data else 0

        # 提取 SQL
        sql_data = next((e["data"] for e in events if e.get("event") == "sql"), None)
        sql_text = (sql_data.get("sql") or "")[:80] if sql_data else ""

        # 提取状态
        state = next((e.get("state") for e in events if e.get("event") == "state_change" and e.get("state") == "completed"), None)
        fallback = next((e for e in events if e.get("event") == "fallback"), None)

        status = "✅" if ok and not fallback else ("⚠️" if fallback else "❌")
        print(f"  {status} 耗时 {elapsed:.2f}s | events={len(events)} | intent={intent_name}({confidence:.2f})")
        if sql_text:
            print(f"     SQL: {sql_text}{'...' if len(sql_text) >= 80 else ''}")
        if fallback:
            print(f"     ⚠️ Fallback: {fallback.get('message', '')[:80]}")
        if not ok:
            print(f"     ❌ Error: {result.get('error')}")

        summary.append({
            "qid": q["id"],
            "label": q["label"],
            "ok": ok,
            "intent": intent_name,
            "confidence": confidence,
            "event_count": len(events),
            "sql_present": bool(sql_text),
            "fallback": bool(fallback),
            "fallback_msg": fallback.get("message", "") if fallback else "",
            "elapsed_sec": round(elapsed, 2),
        })

    # 4. 统计
    print("\n" + "-" * 70)
    print("[3/3] 汇总")
    ok_count = sum(1 for s in summary if s["ok"] and not s["fallback"])
    fb_count = sum(1 for s in summary if s["fallback"])
    err_count = sum(1 for s in summary if not s["ok"])
    print(f"  ✅ 正常完成: {ok_count}/10")
    print(f"  ⚠️ 兜底回复: {fb_count}/10")
    print(f"  ❌ 异常: {err_count}/10")
    print(f"  意图分布: {dict((s['intent'], sum(1 for x in summary if x['intent']==s['intent'])) for s in summary)}")

    # 输出埋点文件路径
    from services.analytics import EVENTS_FILE, count_events
    print(f"\n📁 埋点文件: {EVENTS_FILE}")
    print(f"📊 埋点行数: {count_events()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())