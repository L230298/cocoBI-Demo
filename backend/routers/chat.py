"""对话 API - 流式 SSE"""
from __future__ import annotations
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.orchestrator import Orchestrator
from models.schemas import ChatRequest
from services.dataset_registry import get_dataset

router = APIRouter(prefix="/api/chat", tags=["chat"])
_orchestrator = Orchestrator()


@router.post("")
async def chat(req: ChatRequest):
    """流式对话入口 - 返回 NDJSON 流"""
    if req.dataset_id:
        ds = get_dataset(req.dataset_id)
        if not ds:
            raise HTTPException(
                status_code=404,
                detail={"error_code": "DataSourceUnavailable", "error_msg": "数据集未找到,请先上传"},
            )

    async def event_stream():
        try:
            async for event in _orchestrator.run(
                user_input=req.user_input,
                dataset_id=req.dataset_id or "",
                session_id=req.session_id,
            ):
                yield json.dumps(event, ensure_ascii=False, default=str) + "\n"
        except Exception as e:
            yield json.dumps(
                {
                    "event": "error",
                    "state": "abnormal",
                    "message": "系统开小差了,请稍后再试",
                    "error_code": type(e).__name__,
                },
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
