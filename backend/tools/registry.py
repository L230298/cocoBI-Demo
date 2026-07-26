"""工具注册表 - 实现 PRD §3.3.1 的工具可见性 + 权限控制"""
from __future__ import annotations
from typing import Callable, Any
import asyncio
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """所有 Agent 可见,权限控制谁可调用 - PRD §3.3.1"""

    def __init__(self) -> None:
        self._tools: dict[str, dict] = {}

    def register(
        self,
        name: str,
        func: Callable,
        purpose: str,
        owner_skills: list[str],
        input_schema: dict | None = None,
        output_schema: dict | None = None,
        forbidden_ops: list[str] | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._tools[name] = {
            "name": name,
            "func": func,
            "purpose": purpose,
            "owner_skills": owner_skills,
            "input_schema": input_schema or {},
            "output_schema": output_schema or {},
            "forbidden_ops": forbidden_ops or [],
            "timeout_seconds": timeout_seconds,
        }

    def get(self, name: str) -> dict | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {"name": t["name"], "purpose": t["purpose"], "owner_skills": t["owner_skills"]}
            for t in self._tools.values()
        ]


# 全局单例
_REGISTRY = ToolRegistry()


def register_tool(
    name: str,
    purpose: str,
    owner_skills: list[str],
    input_schema: dict | None = None,
    output_schema: dict | None = None,
    forbidden_ops: list[str] | None = None,
    timeout_seconds: float | None = None,
):
    """装饰器:把函数注册为 Agent 可调用的工具"""

    def deco(func: Callable) -> Callable:
        _REGISTRY.register(
            name=name,
            func=func,
            purpose=purpose,
            owner_skills=owner_skills,
            input_schema=input_schema,
            output_schema=output_schema,
            forbidden_ops=forbidden_ops,
            timeout_seconds=timeout_seconds,
        )
        logger.info(f"Tool registered: {name} (owners={owner_skills})")
        return func

    return deco


def get_tool(name: str) -> dict | None:
    return _REGISTRY.get(name)


async def invoke_tool(name: str, **kwargs) -> dict:
    """统一调用入口:负责超时、错误捕获、违规拦截 - PRD §3.3.2 失败处理"""
    tool = _REGISTRY.get(name)
    if not tool:
        return {"success": False, "error_code": "ToolNotFound", "error_msg": f"工具 {name} 不存在"}

    # SQL 注入防护 - PRD §4.3 安全要求
    if name == "execute_sql":
        sql = kwargs.get("sql", "").lower()
        for forbidden in tool["forbidden_ops"]:
            if forbidden in sql:
                return {
                    "success": False,
                    "error_code": "ForbiddenOperation",
                    "error_msg": f"检测到禁止操作 {forbidden},已拒绝执行",
                }

    timeout = tool["timeout_seconds"]
    try:
        if timeout:
            result = await asyncio.wait_for(
                _safe_call(tool["func"], **kwargs), timeout=timeout
            )
        else:
            result = await _safe_call(tool["func"], **kwargs)
        return result
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error_code": "Timeout",
            "error_msg": f"工具执行超过 {timeout} 秒",
            "retry_after_ms": 1000,
        }
    except Exception as e:
        logger.exception(f"Tool {name} failed")
        return {"success": False, "error_code": type(e).__name__, "error_msg": str(e)}


async def _safe_call(func: Callable, **kwargs) -> dict:
    """支持同步和异步工具函数"""
    if asyncio.iscoroutinefunction(func):
        return await func(**kwargs)
    return await asyncio.to_thread(func, **kwargs)
