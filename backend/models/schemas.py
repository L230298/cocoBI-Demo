"""Pydantic 模型 - 对应 PRD §3 中的所有 JSON Schema"""
from __future__ import annotations
from typing import Literal, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== 意图相关 (PRD §3.1.4) ====================
IntentName = Literal[
    "QueryBasicMetrics",
    "QueryUserCount",
    "QueryCompareAndTopN",
    "QueryTrend",
    "ThresholdAlert",
    "AttributeAnalysis",
    "SmartInterpretation",
    "Unknown",
]


class IntentResult(BaseModel):
    """IntentAgent 输出 - PRD §3.2.2 Agent1"""

    intent: IntentName
    confidence: float = Field(ge=0, le=1)
    slots: dict[str, Any] = Field(default_factory=dict)
    alternatives: list[IntentName] = Field(default_factory=list)
    fallback_message: Optional[str] = None  # PRD §3.1.5 兜底文案


# ==================== Schema 映射 (PRD §3.2.2 Agent2) ====================
class FieldMapping(BaseModel):
    table: str
    name: str
    type: str
    sample: Any = None


class SchemaMapping(BaseModel):
    """SchemaAgent 输出"""

    tables: list[str]
    fields: list[str]
    filters: list[dict] = Field(default_factory=list)
    joins: list[dict] = Field(default_factory=list)
    unmapped_slots: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


# ==================== SQL 生成 (PRD §3.2.2 Agent3) ====================
class SqlResult(BaseModel):
    """NL2SQLAgent 输出"""

    sql: str
    params: dict = Field(default_factory=dict)
    explanation: str = ""
    confidence: float = Field(ge=0, le=1)
    is_executable: bool = True
    validation_errors: list[str] = Field(default_factory=list)


# ==================== 智能解读 / 数据故事 (PRD §3.2.2 Agent4) ====================
class ChartConfig(BaseModel):
    chart_type: Literal["bar", "line", "pie", "funnel", "table"]
    title: str
    data: list[dict]
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    series_field: Optional[str] = None


class Observation(BaseModel):
    """可关注观察点 - 纯文字,不触发外部动作 - PRD §3.2.2 Agent4"""

    text: str
    severity: Literal["info", "warning", "success"] = "info"


class NextStep(BaseModel):
    """下一步建议 - 轻量闭环 - PRD §3.2.2 Agent4"""

    text: str
    type: Literal["compare", "drill", "share", "export", "explore"] = "explore"


class FollowupQuestion(BaseModel):
    """推荐追问 - PRD §1.2/§3.5.2"""

    text: str
    intent_hint: Optional[IntentName] = None


class DataStory(BaseModel):
    """完整数据故事 - StorytellingAgent 输出"""

    story_id: str
    title: str
    summary: str
    sections: list[dict] = Field(default_factory=list)
    charts: list[ChartConfig] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    next_steps: list[NextStep] = Field(default_factory=list)
    recommended_followups: list[FollowupQuestion] = Field(default_factory=list)
    copy_insight_text: str  # 一键复制的洞察文案
    share_url: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence_overall: float = Field(ge=0, le=1, default=0.8)


# ==================== 状态机 (PRD §3.4.6) ====================
AppState = Literal[
    "idle",
    "uploading",
    "validating",
    "requesting",
    "receiving",
    "generating",
    "completed",
    "exporting",
    "abnormal",
]


# ==================== 对话 API ====================
class ChatRequest(BaseModel):
    """/api/chat 入口"""

    session_id: str
    user_input: str = Field(min_length=1, max_length=500)
    dataset_id: Optional[str] = None
    # 多轮对话:之前查询的 intent + slots(用来做"再按城市拆分"等接续识别)
    conversation_history: Optional[list[dict]] = None
    industry_template: Optional[str] = "通用"


class ChatStreamEvent(BaseModel):
    """SSE 流式事件 - 对应 PRD §3.4.6 多个状态"""

    event: Literal[
        "state_change",
        "intent",
        "schema",
        "sql",
        "sql_result",
        "chart",
        "story_chunk",
        "observation",
        "next_step",
        "followup",
        "complete",
        "error",
        "fallback",
    ]
    state: Optional[AppState] = None
    data: Any = None
    message: Optional[str] = None


# ==================== 数据集 API ====================
class DatasetInfo(BaseModel):
    dataset_id: str
    name: str
    industry_template: str
    row_count: int
    column_count: int
    size_bytes: int
    fields: list[FieldMapping]
    business_glossary: dict[str, str] = Field(default_factory=dict)
    uploaded_at: str


class RecentQuery(BaseModel):
    query: str
    intent: IntentName
    timestamp: str
    slots: dict


# ==================== 反馈 API ====================
class FeedbackRequest(BaseModel):
    query_id: str
    feedback_type: Literal["up", "down", "correction"]
    comment: Optional[str] = None
    tags: Optional[list[str]] = None  # 问题分类标签: 有害/不安全 / 虚假信息 / 没有帮助 / 其他
