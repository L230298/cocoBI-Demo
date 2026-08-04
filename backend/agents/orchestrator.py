"""主控 Agent - 编排 IntentAgent → SchemaAgent → NL2SQLAgent → StorytellingAgent
对应 PRD §3.2 流程图
"""
from __future__ import annotations
import asyncio
import re
import time
from typing import AsyncGenerator
from .skills.intent_agent import IntentAgent
from .skills.schema_agent import SchemaAgent
from .skills.nl2sql_agent import NL2SQLAgent
from .skills.storytelling_agent import StorytellingAgent
from tools import invoke_tool
from services.session_service import record_query, update_query_sql, update_query_charts
from services import analytics


def get_query(user_id: str, query_id: str) -> dict | None:
    """P2-1 辅助:从 session_service 拿前序 query 的 SQL 和结果,用于 I5 复用"""
    from services.session_service import _QUERIES  # noqa: F401
    qs = _QUERIES.get(user_id, [])
    for q in qs:
        if q.get("id") == query_id:
            return q
    return None
from services import analytics


# Chitchat 关键词模式: 命中就直接返回功能介绍, 不走数据流
_CHITCHAT_PATTERNS = [
    ("功能", "FEATURES"),
    ("你能做什么", "FEATURES"),
    ("你能干嘛", "FEATURES"),
    ("怎么用", "USAGE"),
    ("怎么操作", "USAGE"),
    ("怎么玩", "USAGE"),
    ("怎么开始", "USAGE"),
    ("怎么上手", "USAGE"),
    ("使用指南", "USAGE"),
    ("使用帮助", "USAGE"),
    ("help", "USAGE"),
    ("介绍", "FEATURES"),
    ("你好", "GREETING"),
    ("hi", "GREETING"),
    ("hello", "GREETING"),
    ("在吗", "GREETING"),
    ("谢谢", "GREETING"),
    ("thanks", "GREETING"),
]

_CHITCHAT_RESPONSES = {
    "FEATURES": (
        "我是 cocoBI, 你的 AI 数据分析助手! 🚀\n\n"
        "【核心功能】\n"
        "1. 📊 自然语言查询: 直接问\"上周 GMV 多少?\"\"哪个品类卖得最好?\", 我帮你查数据\n"
        "2. 📈 自动图表: 查询结果自动生成可视化图表 (柱状/折线/饼图)\n"
        "3. 💡 智能解读: 给出数据洞察和策略建议\n"
        "4. 📋 下载报告: 一键生成 8 章节 Word 数据分析报告 (.docx)\n"
        "5. 🔍 追问推荐: 基于上下文给你下一步分析建议\n"
        "6. 🔗 分享链接: 把分析结果发给同事\n\n"
        "【怎么开始】\n"
        "① 上传你的 Excel / CSV 数据\n"
        "② 用自然语言提问\n"
        "③ 看自动生成的可视化和洞察"
    ),
    "USAGE": (
        "【快速上手 cocoBI】\n\n"
        "① 上传数据 - 点输入框旁的 + 上传数据 按钮, 选择 Excel (.xlsx) 或 CSV 文件\n"
        "② 选数据集 - 顶部下拉选刚上传的数据集\n"
        "③ 提问 - 用自然语言问, 例如:\n"
        "   • \"上周 GMV 是多少?\"\n"
        "   • \"最近什么卖得好?TOP 10\"\n"
        "   • \"为什么这个月订单掉了?\"\n"
        "④ 看结果 - 自动生成图表 + 数据洞察\n"
        "⑤ 生成报告 - 点 生成数据分析报告 下载完整 .docx\n\n"
        "💡 【小贴士】\n"
        "• 问题越具体越好 (带时间范围 / 维度)\n"
        "• 不确定怎么问? 直接说\"你能做什么\"就行"
    ),
    "GREETING": (
        "你好! 👋 我是 cocoBI 数据分析助手\n\n"
        "我能帮你: 上传数据 → 自然语言提问 → 自动生成图表 + 报告\n\n"
        "如果你是第一次用, 可以问我:\n"
        "• \"你能做什么?\" - 看功能介绍\n"
        "• \"怎么用?\" - 看上手指南\n"
        "• 或者直接问\"上周 GMV 多少?\" 试试效果"
    ),
}


def _detect_chitchat(user_input: str) -> dict | None:
    """检测是否是闲聊/非数据问题, 命中返回 Chitchat 响应
    返回: dict {title, summary} 或 None
    """
    text = (user_input or "").strip()
    if not text or len(text) > 50:
        # 太长一般是真问题, 不当闲聊
        return None
    for kw, resp_type in _CHITCHAT_PATTERNS:
        if kw in text.lower():
            content = _CHITCHAT_RESPONSES[resp_type]
            return {
                "type": resp_type,
                "summary": content,
                "title": "cocoBI 使用指南" if resp_type != "GREETING" else "你好",
            }
    return None


class Orchestrator:
    """主控 Agent:流水线 4 个 Skill,SSE 推送每个阶段结果"""

    def __init__(self) -> None:
        self.intent_agent = IntentAgent()
        self.schema_agent = SchemaAgent()
        self.nl2sql_agent = NL2SQLAgent()
        self.storytelling_agent = StorytellingAgent()

    async def run(
        self, user_input: str, dataset_id: str, session_id: str, user_id: str = "default",
        conversation_history: list | None = None
    ) -> AsyncGenerator[dict, None]:
        """SSE 流式输出 - 对应 PRD §3.4.6 状态变化"""
        history = conversation_history or []
        full_result: dict = {
            "dataset_id": dataset_id,
            "user_input": user_input,
            "conversation_history": history,
        }

        # ============ 埋点: query_submitted ============
        analytics.record_event(
            event_type="query_submitted",
            user_input=user_input,
            session_id=session_id,
            extra={"dataset_id": dataset_id, "user_id": user_id},
        )

        # ============ 阶段 1: IntentAgent ============
        yield {"event": "state_change", "state": "requesting", "message": "正在理解您的问题..."}
        await asyncio.sleep(0.1)

        # Chitchat 快速通道: 命中关键词就直接返回功能介绍, 不走 LLM 也不走数据流
        chitchat_resp = _detect_chitchat(user_input)
        if chitchat_resp:
            # 埋点: chitchat 也记一条 intent_recognized (intent=Chitchat)
            analytics.record_event(
                event_type="intent_recognized",
                user_input=user_input,
                session_id=session_id,
                intent_recognized="Chitchat",
                intent_confidence=1.0,
                slots={"type": chitchat_resp["type"]},
            )
            # P2-2 修复: Chitchat 跳过 StorytellingAgent,不输出 next_steps / followups
            # 语义上 Chitchat 不应该输出"下一步建议",闭环边界校验
            yield {"event": "intent", "data": {"intent": "Chitchat", "confidence": 1.0, "slots": {}, "alternatives": []}}
            yield {"event": "chitchat", "data": chitchat_resp}
            yield {"event": "state_change", "state": "completed", "message": "回复完成"}
            yield {"event": "complete", "data": {"title": "cocoBI 使用指南", "summary": chitchat_resp["summary"], "chitchat": True, "next_steps_count": 0, "followups_count": 0}}
            return

        intent_result = await self.intent_agent.run(
            user_input, session_history=history
        )
        full_result["intent"] = intent_result["intent"]
        full_result["slots"] = intent_result.get("slots", {})
        full_result["confidence"] = intent_result.get("confidence", 0)
        query_id = record_query(
            user_id, user_input, intent_result["intent"], intent_result.get("slots", {})
        )
        full_result["query_id"] = query_id

        # ============ 埋点: intent_recognized ============
        analytics.record_event(
            event_type="intent_recognized",
            user_input=user_input,
            session_id=session_id,
            query_id=query_id,
            intent_recognized=intent_result["intent"],
            intent_confidence=intent_result.get("confidence", 0),
            slots=intent_result.get("slots", {}),
            extra={"alternatives": intent_result.get("alternatives", [])},
        )

        yield {"event": "intent", "data": intent_result, "query_id": query_id}

        # 兜底 - PRD §3.1.5
        if intent_result.get("fallback_message"):
            analytics.record_event(
                event_type="error_occurred",
                user_input=user_input,
                session_id=session_id,
                query_id=query_id,
                intent_recognized=intent_result["intent"],
                error_code="INTENT_FALLBACK",
                error_stage="intent",
                error_msg=intent_result["fallback_message"],
            )
            yield {
                "event": "fallback",
                "state": "abnormal",
                "message": intent_result["fallback_message"],
                "data": intent_result,
            }
            return

        # ============ 阶段 2: SchemaAgent ============
        yield {"event": "state_change", "state": "receiving", "message": "正在映射数据表..."}
        slots_with_input = dict(intent_result.get("slots", {}))
        slots_with_input["_user_input"] = user_input
        schema_result = await self.schema_agent.run(
            intent=intent_result["intent"],
            slots=slots_with_input,
            dataset_id=dataset_id,
        )
        full_result["schema"] = schema_result

        # ============ 埋点: schema_mapped (扩展埋点,PRD 列表之外) ============
        analytics.record_event(
            event_type="schema_mapped",
            user_input=user_input,
            session_id=session_id,
            query_id=query_id,
            intent_recognized=intent_result["intent"],
            schema_mapped=schema_result,
            extra={"confidence": schema_result.get("confidence")},
        )

        yield {"event": "schema", "data": schema_result}

        # P0-1 数据降级: 业务术语命中但数据集缺字段,返回友好提示
        if schema_result.get("fallback_message"):
            analytics.record_event(
                event_type="error_occurred",
                user_input=user_input,
                session_id=session_id,
                query_id=query_id,
                intent_recognized=intent_result["intent"],
                error_code="TERM_FIELDS_MISSING",
                error_stage="schema",
                error_msg=schema_result["fallback_message"],
                extra={"term_mappings": schema_result.get("term_mappings")},
            )
            yield {
                "event": "fallback",
                "state": "abnormal",
                "message": schema_result["fallback_message"],
                "data": schema_result,
            }
            return

        if schema_result.get("confidence", 0) < 0.5:
            analytics.record_event(
                event_type="error_occurred",
                user_input=user_input,
                session_id=session_id,
                query_id=query_id,
                intent_recognized=intent_result["intent"],
                error_code="SCHEMA_LOW_CONFIDENCE",
                error_stage="schema",
                error_msg="未找到匹配的数据字段,请检查数据集",
                extra={"confidence": schema_result.get("confidence")},
            )
            yield {
                "event": "fallback",
                "state": "abnormal",
                "message": "未找到匹配的数据字段,请检查数据集",
                "data": schema_result,
            }
            return

        # ============ 阶段 3: NL2SQLAgent ============
        # P2-1 修复 (BC-004): I5 (SmartInterpretation) 优先复用前序 query 的 SQL/数据
        # 而不是触发新查询。语义上"解释一下"就是解读前置结果。
        previous_query_id = ""
        reused_from_previous = False
        if intent_result["intent"] == "SmartInterpretation" and history:
            # 找最近一条非 I5 的同 dataset 查询
            for h in reversed(history):
                if h.get("intent") in ("QueryBasicMetrics", "QueryCompareAndTopN",
                                       "QueryTrend", "QueryUserCount",
                                       "ThresholdAlert", "AttributeAnalysis"):
                    if not h.get("dataset_id") or h.get("dataset_id") == dataset_id:
                        previous_query_id = h.get("query_id", "")
                        reused_from_previous = True
                        break

        if reused_from_previous and previous_query_id:
            # 从 session 复用前序的 SQL/结果,跳过 NL2SQL 新查询
            previous = get_query(user_id, previous_query_id)
            if previous and previous.get("sql"):
                sql_result = {
                    "sql": previous.get("sql", ""),
                    "params": {},
                    "explanation": f"P2-1 复用前序 query {previous_query_id} 的 SQL,不再新查询",
                    "confidence": 0.9,
                    "is_executable": True,
                    "validation_errors": [],
                    "reused_from_previous": True,
                }
                full_result["sql"] = sql_result
                full_result["previous_query_id"] = previous_query_id
                # 直接复用前序的 sql_result
                exec_result = previous.get("sql_result") or {
                    "success": True,
                    "rows": previous.get("rows", []),
                    "row_count": len(previous.get("rows", [])),
                }
                # 立即补埋点: sql_generated + sql_executed (复用状态)
                analytics.record_event(
                    event_type="sql_generated",
                    user_input=user_input,
                    session_id=session_id,
                    query_id=query_id,
                    intent_recognized=intent_result["intent"],
                    sql_generated=sql_result["sql"],
                    sql_confidence=0.9,
                    sql_retry_count=0,
                    extra={"is_executable": True, "reused_from_previous": True, "previous_query_id": previous_query_id},
                )
                yield {"event": "state_change", "state": "generating", "message": f"复用前序分析结果({previous_query_id})..."}
                yield {"event": "sql", "data": sql_result}
                analytics.record_event(
                    event_type="sql_executed",
                    user_input=user_input,
                    session_id=session_id,
                    query_id=query_id,
                    intent_recognized=intent_result["intent"],
                    sql_generated=sql_result["sql"],
                    sql_executed_status="success",
                    sql_elapsed_ms=0,  # 复用,无新查询耗时
                    row_count=exec_result.get("row_count"),
                    extra={"reused_from_previous": True},
                )
                yield {"event": "sql_result", "data": exec_result}
                full_result["sql_result"] = exec_result
                # 跳到 StorytellingAgent
                yield {"event": "state_change", "state": "generating", "message": "正在生成数据故事..."}
                story = await self.storytelling_agent.run(
                    full_result=full_result,
                    user_context={"session_id": session_id, "user_id": user_id},
                )
                # 埋点
                next_steps_count = len(story.get("next_steps", []) or [])
                followups_count = len(story.get("recommended_followups", []) or [])
                analytics.record_event(
                    event_type="story_generated",
                    user_input=user_input,
                    session_id=session_id,
                    query_id=query_id,
                    intent_recognized=intent_result["intent"],
                    sql_generated=sql_result["sql"],
                    story_generated={
                        "title": story.get("title"),
                        "summary": story.get("summary"),
                        "sections_count": len(story.get("sections", []) or []),
                        "observations_count": len(story.get("observations", []) or []),
                        "has_charts": bool(story.get("charts")),
                    },
                    next_steps_count=next_steps_count,
                    followups_count=followups_count,
                    extra={"reused_from_previous": True},
                )
                for obs in story.get("observations", []):
                    yield {"event": "observation", "data": obs}
                    await asyncio.sleep(0.05)
                for step in story.get("next_steps", []):
                    yield {"event": "next_step", "data": step}
                    await asyncio.sleep(0.05)
                for fu in story.get("recommended_followups", []):
                    yield {"event": "followup", "data": fu}
                    await asyncio.sleep(0.05)
                yield {"event": "state_change", "state": "completed", "message": "分析完成"}
                yield {"event": "complete", "data": story}
                if query_id and story.get("charts"):
                    update_query_charts(user_id, query_id, story.get("charts") or [])
                return

        # 兜底: I5 没有前序数据时,按"最近 7 天"默认值生成新查询
        if intent_result["intent"] == "SmartInterpretation" and not (reused_from_previous and previous_query_id):
            # 用上一轮 schema_result 走完整 NL2SQL,但 metric/time 兜底
            if not intent_result.get("slots", {}).get("时间范围"):
                intent_result.setdefault("slots", {})["时间范围"] = "最近7天"
                slots = dict(intent_result.get("slots", {}))
                slots["时间范围"] = "最近7天"
                intent_result["slots"] = slots

        yield {"event": "state_change", "state": "generating", "message": "正在生成查询语句..."}
        sql_result = await self.nl2sql_agent.run(
            intent=intent_result["intent"],
            slots=intent_result.get("slots", {}),
            mapped_query=schema_result,
            dataset_id=dataset_id,
            user_input=user_input,
        )
        full_result["sql"] = sql_result

        # ============ 埋点: sql_generated ============
        analytics.record_event(
            event_type="sql_generated",
            user_input=user_input,
            session_id=session_id,
            query_id=query_id,
            intent_recognized=intent_result["intent"],
            sql_generated=sql_result.get("sql", ""),
            sql_confidence=sql_result.get("confidence"),
            sql_retry_count=sql_result.get("retry_count", 0),
            extra={"is_executable": sql_result.get("is_executable")},
        )

        yield {"event": "sql", "data": sql_result}
        if sql_result.get("sql") and query_id:
            update_query_sql(user_id, query_id, sql_result["sql"])

        if not sql_result.get("is_executable"):
            analytics.record_event(
                event_type="error_occurred",
                user_input=user_input,
                session_id=session_id,
                query_id=query_id,
                intent_recognized=intent_result["intent"],
                sql_generated=sql_result.get("sql", ""),
                error_code="SQL_NOT_EXECUTABLE",
                error_stage="nl2sql",
                error_msg=sql_result.get("fallback_message", "SQL 生成失败"),
                extra={"validation_errors": sql_result.get("validation_errors", [])},
            )
            yield {
                "event": "fallback",
                "state": "abnormal",
                "message": sql_result.get("fallback_message", "SQL 生成失败"),
                "data": sql_result,
            }
            return

        # 执行 SQL - 埋点 sql_executed
        sql_start = time.time()
        try:
            exec_result = await invoke_tool(
                "execute_sql", sql=sql_result["sql"], dataset_id=dataset_id
            )
        except Exception as e:
            sql_elapsed_ms = int((time.time() - sql_start) * 1000)
            analytics.record_event(
                event_type="error_occurred",
                user_input=user_input,
                session_id=session_id,
                query_id=query_id,
                intent_recognized=intent_result["intent"],
                sql_generated=sql_result.get("sql", ""),
                sql_elapsed_ms=sql_elapsed_ms,
                error_code=type(e).__name__,
                error_stage="execute_sql",
                error_msg=str(e),
            )
            raise
        sql_elapsed_ms = int((time.time() - sql_start) * 1000)
        full_result["sql_result"] = exec_result

        # ============ 埋点: sql_executed ============
        analytics.record_event(
            event_type="sql_executed",
            user_input=user_input,
            session_id=session_id,
            query_id=query_id,
            intent_recognized=intent_result["intent"],
            sql_generated=sql_result.get("sql", ""),
            sql_executed_status="success" if exec_result.get("success") else "fail",
            sql_elapsed_ms=sql_elapsed_ms,
            row_count=exec_result.get("row_count"),
            extra={"error_msg": exec_result.get("error_msg")} if not exec_result.get("success") else None,
        )

        yield {"event": "sql_result", "data": exec_result}

        # ============ 阶段 4: StorytellingAgent ============
        yield {"event": "state_change", "state": "generating", "message": "正在生成数据故事..."}
        story = await self.storytelling_agent.run(
            full_result=full_result,
            user_context={"session_id": session_id, "user_id": user_id},
        )

        # ============ 埋点: story_generated ============
        next_steps_count = len(story.get("next_steps", []) or [])
        followups_count = len(story.get("recommended_followups", []) or [])
        analytics.record_event(
            event_type="story_generated",
            user_input=user_input,
            session_id=session_id,
            query_id=query_id,
            intent_recognized=intent_result["intent"],
            sql_generated=sql_result.get("sql", ""),
            story_generated={
                "title": story.get("title"),
                "summary": story.get("summary"),
                "sections_count": len(story.get("sections", []) or []),
                "observations_count": len(story.get("observations", []) or []),
                "has_charts": bool(story.get("charts")),
            },
            next_steps_count=next_steps_count,
            followups_count=followups_count,
        )

        # 流式推送报告各部分 - PRD §3.4.6 "生成中" 状态
        for obs in story.get("observations", []):
            yield {"event": "observation", "data": obs}
            await asyncio.sleep(0.05)
        for step in story.get("next_steps", []):
            yield {"event": "next_step", "data": step}
            await asyncio.sleep(0.05)
        for fu in story.get("recommended_followups", []):
            yield {"event": "followup", "data": fu}
            await asyncio.sleep(0.05)

        yield {"event": "state_change", "state": "completed", "message": "分析完成"}
        yield {"event": "complete", "data": story}

        if query_id and story.get("charts"):
            update_query_charts(user_id, query_id, story.get("charts") or [])