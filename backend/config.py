"""全局配置 - 从 PRD §3-§4 提取的约束"""
from pathlib import Path
import os

# 服务配置
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8000))
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://192.168.5.143:5173",
    "http://192.168.5.143:5180",
]
_extra = os.environ.get("ALLOWED_ORIGINS", "")
if _extra:
    CORS_ORIGINS.extend([o.strip() for o in _extra.split(",") if o.strip()])
CORS_ORIGINS.append("*")
# 数据规模限制 (PRD §4.1)
MAX_DATASET_SIZE_MB = 50
MAX_ROWS_PER_DATASET = 100_000
MAX_DS_PER_USER = 10

# 性能阈值 (PRD §4.1)
SQL_TIMEOUT_SECONDS = 5
CHART_RENDER_TIMEOUT_SECONDS = 3
LLM_MOCK_DELAY_MS = 500

# 路径 - 支持 Railway Volume 持久化
# Railway 部署时挂载 Volume 到 /app/data(整目录持久)
# 本地开发用 ./data
_BACKEND_DIR = Path(__file__).parent
_BASE_DIR = Path("/app/data") if Path("/app").exists() else _BACKEND_DIR / "data"

DATA_DIR = _BASE_DIR
SAMPLES_DIR = _BASE_DIR / "samples"
UPLOAD_DIR = _BASE_DIR / "uploads"
EXPORT_DIR = _BASE_DIR / "exports"
LOG_DIR = _BASE_DIR / "logs"

# 确保目录存在
for d in [DATA_DIR, SAMPLES_DIR, UPLOAD_DIR, EXPORT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# 意图定义 (PRD §3.1.4 核心 5 + 后续扩的 1)
INTENT_REGISTRY = {
    "QueryBasicMetrics": {
        "name": "基础问数",
        "description": "查询单值指标",
        "default_time_range": "最近7天",
        "required_slots": ["指标", "时间范围"],
    },
    "QueryCompareAndTopN": {
        "name": "多维对比与TopN",
        "description": "排序、对比、排名",
        "default_time_range": "最近30天",
        "default_top_n": 10,
    },
    "ThresholdAlert": {
        "name": "阈值预警",
        "description": "指标是否超出阈值",
    },
    "AttributeAnalysis": {
        "name": "归因分析",
        "description": "解释指标波动原因",
        "default_dimensions": ["品类", "店铺", "渠道", "地区"],
    },
    "SmartInterpretation": {
        "name": "智能解读",
        "description": "对数据结果自动生成自然语言解读",
    },
    # 后续扩展: 跟 schemas.py IntentName Literal 对齐, 避免「意图越界」BadCase
    "QueryTrend": {
        "name": "趋势分析",
        "description": "查询指标随时间的变化趋势(每日/每周/月度)",
        "default_time_range": "最近30天",
        "required_slots": ["指标", "时间范围"],
    },
}


# 报告模板 (PRD §3.2.2 StorytellingAgent Prompt)
REPORT_TEMPLATE = {
    "sections": [
        {"id": 1, "title": "报告基本信息", "description": "包含报告名称、报告日期、报告周期、数据更新时间、报告责任人等基础信息"},
        {"id": 2, "title": "业务背景与分析目标", "description": "阐述本次分析的业务场景、核心问题、分析目的及预期产出"},
        {"id": 3, "title": "指标体系与统计口径", "description": "列出报告涉及的核心指标,并明确各指标的计算公式、统计口径及维度说明"},
        {"id": 4, "title": "数据来源与质量说明", "description": "标注数据来源系统、数据抽取时间、数据清洗规则及数据质量评价"},
        {"id": 5, "title": "指标报表展示", "description": "以可视化图表呈现核心指标的趋势、分布及对比结果"},
        {"id": 6, "title": "异常与归因分析", "description": "识别指标异常波动,通过多维度拆解定位根因"},
        {"id": 7, "title": "策略建议与行动计划", "description": "基于归因分析结论,提出可落地的优化策略、改进措施及后续跟踪计划"},
        {"id": 8, "title": "附录", "description": "包含详细数据表、SQL查询语句、计算逻辑说明及补充材料"},
    ],
    "version": "1.0",
}


# 友好错误文案 (PRD §3.4.7)
FRIENDLY_ERRORS = {
    "LLM_API_Timeout": "问题有点复杂,我再想想...",
    "LLM_NonJSON": "正在重新组织答案...",
    "ConcurrencyLimit": "当前用户较多,排队中...",
    "DataSourceUnavailable": "数据源暂时无法访问,请刷新",
    "SQL_Timeout": "查询较慢,我换种方式试试",
    "SQL_SyntaxError": "这个问题有点复杂,要不要换个问法",
    "Dataset_FormatError": "上传失败:请检查文件格式",
    "File_TooLarge": f"文件过大,超过 {MAX_DATASET_SIZE_MB}MB 限制",
}


# 兜底回复模板 (PRD §3.1.5)
FALLBACK_PROMPTS = {
    "intent_unknown": "我不太确定您想问什么,您是想:①问销量 ②查阈值 ③分析原因?",
    "slot_missing": "您没指定时间,我用「最近7天」代替可以吗?",
    "sql_failed": "这个问题比较复杂,我暂时答不上来,要不要换个问法?",
    "no_data": "这段时间没有相关数据,您要不要换个时间范围?",
    "no_attribution": "没发现明显异常,可能属于自然波动",
}
