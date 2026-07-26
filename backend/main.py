"""cocoBI 后端入口 - FastAPI"""
from __future__ import annotations
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import HOST, PORT, CORS_ORIGINS, SAMPLES_DIR
from routers import chat, dataset, story, feedback

# 导入所有工具以触发注册 - PRD §3.3.1
import tools  # noqa: F401
from tools import execute_sql  # noqa: F401
from tools import get_data_source_metadata  # noqa: F401
from tools import render_chart  # noqa: F401
from tools import export_data_story  # noqa: F401
from tools import get_recent_queries  # noqa: F401
from tools import collect_user_feedback  # noqa: F401
from tools import generate_next_steps  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时自动注册示例数据集"""
    from services.dataset_loader import parse_uploaded_file

    sample = SAMPLES_DIR / "retail_20260720_gmv.csv"
    if sample.exists():
        try:
            info = parse_uploaded_file(
                sample,
                dataset_name="示例-零售 GMV",
                industry_template="零售",
            )
            logger.info(f"示例数据集已加载: {info['dataset_id']} ({info['row_count']} 行)")
        except Exception as e:
            logger.warning(f"示例数据集加载失败: {e}")

    yield


app = FastAPI(
    title="cocoBI Demo",
    description="AI 数据分析助手 - 4 Agent 协作 + 7 工具 + 轻量闭环",
    version="1.0.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理 - PRD §3.4.7
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.url}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": type(exc).__name__,
            "error_msg": "系统开小差了,请稍后再试",  # 友好提示,不暴露技术细节
        },
    )


app.include_router(chat.router)
app.include_router(dataset.router)
app.include_router(story.router)
app.include_router(feedback.router)


@app.get("/")
async def root():
    return {
        "name": "cocoBI Demo",
        "version": "1.0.1",
        "docs": "/docs",
        "agents": ["IntentAgent", "SchemaAgent", "NL2SQLAgent", "StorytellingAgent"],
        "tools_count": 7,
        "intents": [
            "QueryBasicMetrics",
            "QueryCompareAndTopN",
            "ThresholdAlert",
            "AttributeAnalysis",
            "SmartInterpretation",
        ],
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
