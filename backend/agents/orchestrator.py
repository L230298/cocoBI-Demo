"""主控 Agent - 编排 IntentAgent → SchemaAgent → NL2SQLAgent → StorytellingAgent
对应 PRD §3.2 流程图
"""
from __future__ import annotations
import asyncio
from typing import AsyncGenerator
from .skills.intent_agent import IntentAgent
from .skills.schema_agent import SchemaAgent
from .skills.nl2sql_agent import NL2SQLAgent
from .skills.storytelling_agent import StorytellingAgent
from tools import invoke_tool
from services.session_service import record_query


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

        # ============ 阶段 1: IntentAgent ============
        yield {"event": "state_change", "state": "requesting", "message": "正在理解您的问题..."}
        await asyncio.sleep(0.1)

        intent_result = await self.intent_agent.run(
            user_input, session_history=history
        )
        full_result["intent"] = intent_result["intent"]
        full_result["slots"] = intent_result.get("slots", {})
        full_result["confidence"] = intent_result.get("confidence", 0)
        record_query(user_id, user_input, intent_result["intent"], intent_result.get("slots", {}))

        yield {"event": "intent", "data": intent_result}

        # 兜底 - PRD §3.1.5
        if intent_result.get("fallback_message"):
            yield {
                "event": "fallback",
                "state": "abnormal",
                "message": intent_result["fallback_message"],
                "data": intent_result,
            }
            return

        # ============ 阶段 2: SchemaAgent ============
        yield {"event": "state_change", "state": "receiving", "message": "正在映射数据表..."}
        # 把 user_input 传给 schema agent(用于数据清洗默认判断)
        slots_with_input = dict(intent_result.get("slots", {}))
        slots_with_input["_user_input"] = user_input
        schema_result = await self.schema_agent.run(
            intent=intent_result["intent"],
            slots=slots_with_input,
            dataset_id=dataset_id,
        )
        full_result["schema"] = schema_result
        yield {"event": "schema", "data": schema_result}

        if schema_result.get("confidence", 0) < 0.5:
            yield {
                "event": "fallback",
                "state": "abnormal",
                "message": "未找到匹配的数据字段,请检查数据集",
                "data": schema_result,
            }
            return

        # ============ 阶段 3: NL2SQLAgent ============
        yield {"event": "state_change", "state": "generating", "message": "正在生成查询语句..."}
        sql_result = await self.nl2sql_agent.run(
            intent=intent_result["intent"],
            slots=intent_result.get("slots", {}),
            mapped_query=schema_result,
            dataset_id=dataset_id,
        )
        full_result["sql"] = sql_result
        yield {"event": "sql", "data": sql_result}

        # 兜底
        if not sql_result.get("is_executable"):
            yield {
                "event": "fallback",
                "state": "abnormal",
                "message": sql_result.get("fallback_message", "SQL 生成失败"),
                "data": sql_result,
            }
            return

        # 执行 SQL
        exec_result = await invoke_tool(
            "execute_sql", sql=sql_result["sql"], dataset_id=dataset_id
        )
        full_result["sql_result"] = exec_result
        yield {"event": "sql_result", "data": exec_result}

        # ============ 阶段 4: StorytellingAgent ============
        yield {"event": "state_change", "state": "generating", "message": "正在生成数据故事..."}
        story = await self.storytelling_agent.run(
            full_result=full_result,
            user_context={"session_id": session_id, "user_id": user_id},
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
