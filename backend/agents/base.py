"""Agent 基类 - 统一调用接口"""
from __future__ import annotations
from typing import Any
from services.llm_service import mock_call


class BaseAgent:
    """所有 Agent 的统一接口"""

    name: str = "base"
    system_prompt: str = ""

    def __init__(self, name: str, system_prompt: str = "") -> None:
        self.name = name
        self.system_prompt = system_prompt

    async def run(self, input_data: dict) -> dict:
        """调用 Mock LLM"""
        result = await mock_call(self.name, input_data)
        return result
