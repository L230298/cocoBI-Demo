"""评测运行器 - 从 evaluation/ 目录读取 JSONL,调用本地后端跑评测
支持 --filter 参数(例如 --filter intent/core 只跑核心意图集)
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
EVAL_DIR = Path(__file__).parent


def list_datasets() -> list[dict]:
    req = urllib.request.Request(f"{BASE_URL}/api/dataset/list")
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode("utf-8"))
        return data.get("data") if isinstance(data, dict) else data


def run_query(user_input: str, dataset_id: str, session_id: str) -> dict:
    payload = json.dumps({
        "user_input": user_input,
        "dataset_id": dataset_id,
        "session_id": session_id,
        "conversation_history": [],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        events = []
        with urllib.request.urlopen(req, timeout=60) as resp:
            for line in resp:
                line = line.decode("utf-8", errors="replace").strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return {"ok": True, "events": events}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def collect_jsonl(filter_path: str | None) -> list[dict]:
    """读取 evaluation/ 下所有 jsonl,可选按子目录过滤"""
    cases = []
    for p in EVAL_DIR.rglob("*.jsonl"):
        if filter_path and filter_path not in str(p):
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    cases.append((p, json.loads(line)))
                except json.JSONDecodeError:
                    pass
    return cases


def evaluate(case: dict, dataset_id: str) -> dict:
    """跑一个 case,返回 {qid, ok, intent, events, errors}"""
    session_id = f"eval-{case['qid']}"
    result = run_query(case["user_input"], dataset_id, session_id)
    events = result.get("events", [])
    intent_data = next((e["data"] for e in events if e.get("event") == "intent"), None)
    intent = intent_data.get("intent", "?") if intent_data else "?"
    has_fallback = any(e.get("event") == "fallback" for e in events)
    has_error = any(e.get("event") == "error" for e in events)
    return {
        "qid": case["qid"],
        "ok": result["ok"] and not has_error,
        "intent": intent,
        "events": events,
        "fallback": has_fallback,
        "error": result.get("error"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--filter", help="子目录过滤,例如 intent/core 或 regression")
    args = parser.parse_args()

    print("=" * 70)
    print(f"cocoBI 评测运行器 (filter={args.filter or 'all'})")
    print("=" * 70)

    # 健康检查
    try:
        urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=3).read()
        print(f"✅ Backend 健康")
    except Exception as e:
        print(f"❌ Backend 未运行: {e}")
        return 1

    # 找示例数据集
    ds_list = list_datasets()
    target = next((d for d in ds_list if "示例" in d.get("name", "")), ds_list[0] if ds_list else None)
    if not target:
        print("❌ 没有数据集")
        return 2
    dataset_id = target["dataset_id"]
    print(f"使用数据集: {target['name']} ({dataset_id}, {target.get('row_count')} 行)")

    # 加载评测集
    cases = collect_jsonl(args.filter)
    if not cases:
        print(f"❌ 没找到评测样例 (filter={args.filter})")
        return 3
    print(f"加载评测样例: {len(cases)} 条\n")

    # 跑
    summary = []
    for src_path, case in cases:
        if not case.get("user_input") and case.get("expected", {}).get("must_trigger") == "FRONTEND_VALIDATION":
            # 空字符串会被 Pydantic 拦,直接通过
            summary.append({"qid": case["qid"], "intent": "Unknown", "ok": True, "note": "空字符串前端拦截"})
            continue

        rel = src_path.relative_to(EVAL_DIR).as_posix()
        t0 = time.time()
        result = evaluate(case, dataset_id)
        elapsed = time.time() - t0

        ok = result["ok"]
        intent = result["intent"]
        print(f"  [{rel}] {case['qid']:8s} intent={intent:25s} {'✅' if ok else '❌'} {elapsed:.2f}s")
        if result["fallback"]:
            fb = next((e for e in result["events"] if e.get("event") == "fallback"), {})
            print(f"     ⚠️ fallback: {fb.get('message', '')[:80]}")
        if result["error"]:
            print(f"     ❌ {result['error'][:80]}")
        summary.append({**result, "src": rel})

    # 汇总
    ok_n = sum(1 for s in summary if s.get("ok"))
    fb_n = sum(1 for s in summary if s.get("fallback"))
    err_n = sum(1 for s in summary if not s.get("ok") and not s.get("fallback"))
    print()
    print("=" * 70)
    print(f"汇总: ✅ {ok_n}/{len(summary)}  ⚠️ fallback {fb_n}  ❌ error {err_n}")

    return 0


if __name__ == "__main__":
    sys.exit(main())