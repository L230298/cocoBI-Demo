# cocoBI Demo

> 基于 PRD 自动生成的可运行 Demo
> 产品:cocoBI - AI 数据分析助手 v1.0.1

## ✨ 功能

- 🤖 **4 Agent 流水线**:IntentAgent → SchemaAgent → NL2SQLAgent → StorytellingAgent
- 🛠️ **7 工具**:execute_sql / get_data_source_metadata / render_chart / export_data_story / get_recent_queries / collect_user_feedback / generate_next_steps
- 🎯 **5 意图**:基础问数 / 多维对比 TopN / 阈值预警 / 归因分析 / 智能解读
- 🔄 **轻量闭环**:推荐追问 + 一键复制 + 短链分享(纯文字,绝不触发外部动作)
- 📊 **9 状态机**:完整覆盖 PRD §3.4.6

## 🚀 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
python main.py
# 服务运行在 http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 前端

```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

打开浏览器访问 **http://localhost:5173** 即可。

## 📁 项目结构

```
cocobi-demo/
├── backend/
│   ├── main.py                  # FastAPI 入口
│   ├── config.py                # 全局配置(从 PRD 提取)
│   ├── models/schemas.py        # Pydantic 模型 = PRD JSON Schema
│   ├── agents/
│   │   ├── base.py              # Agent 基类
│   │   ├── orchestrator.py      # 主控 Agent(SSE 流式编排)
│   │   └── skills/              # 4 个 Skill Agent
│   │       ├── intent_agent.py
│   │       ├── schema_agent.py
│   │       ├── nl2sql_agent.py
│   │       └── storytelling_agent.py
│   ├── tools/                   # 7 个工具实现
│   ├── services/
│   │   ├── llm_service.py       # Mock LLM(无需 API Key)
│   │   ├── dataset_registry.py
│   │   ├── dataset_loader.py
│   │   └── session_service.py
│   ├── routers/
│   │   ├── chat.py              # 流式对话
│   │   ├── dataset.py           # 上传/列表/删除
│   │   ├── story.py             # 短链预览
│   │   └── feedback.py          # 反馈 + 工具列表
│   └── data/
│       ├── samples/             # 内置示例数据
│       ├── uploads/             # 用户上传
│       └── exports/             # 导出的数据故事
└── frontend/
    ├── src/
    │   ├── App.tsx              # 状态机驱动主应用
    │   ├── types/               # TypeScript 类型
    │   ├── api/client.ts        # API 封装
    │   ├── hooks/useAnalysis.ts # 核心 hook
    │   ├── utils/stateMachine.ts
    │   └── components/          # 7 个组件
    └── package.json
```

## 🧪 试用问句

启动后,在前端输入框试试这些:

| 问题 | 触发意图 |
|------|---------|
| 上周 GMV 是多少? | QueryBasicMetrics |
| 最近什么卖得好?TOP 10 | QueryCompareAndTopN |
| 为什么这个月订单掉了? | AttributeAnalysis |
| 库存低于 100 的 SKU 有哪些? | ThresholdAlert |
| 解释一下最近的销售趋势 | SmartInterpretation |

## 📐 架构图

```
用户输入 ──→ ChatInput (PRD §3.5.2.1)
              │
              ▼
        Orchestrator (SSE 流)
              │
   ┌──────────┼──────────┬──────────────┐
   ▼          ▼          ▼              ▼
IntentAgent SchemaAgent NL2SQLAgent  StorytellingAgent
   │          │          │              │
   │          │          ▼              │
   │          │     execute_sql         │
   │          │          │              ▼
   │          │          │       render_chart
   │          │          │       export_data_story
   │          │          ▼       generate_next_steps
   │          └────────→ 全量 result ───┐
   │                                    ▼
   └──→ IntentResult ──────── 状态机 9 态 ──→ 前端
```

## 🛡️ 安全特性(PRD §4.3)

- ✅ SQL 白名单:仅允许 SELECT,严禁 DROP/DELETE/UPDATE/INSERT/TRUNCATE/ALTER/CREATE
- ✅ 友好错误:技术错误转换为用户可读提示(§3.4.7)
- ✅ 轻量闭环边界:`generate_next_steps` 纯文字,绝不调用外部 API
- ✅ PII 检测:导出时默认脱敏(留接口)
- ✅ 异常兜底:每个工具超时/失败有降级策略

## 📜 PRD 来源

由 jingsis-prd-generate 格式的 PRD 自动生成。
原 PRD 路径:cocoBI v1.0.1(2026-04-19)

## ⚙️ 配置选项

修改 `backend/config.py`:

- `MAX_DATASET_SIZE_MB`:上传文件大小限制(默认 50)
- `SQL_TIMEOUT_SECONDS`:SQL 执行超时(默认 5s)
- `LLM_MOCK_DELAY_MS`:模拟 LLM 响应延迟(默认 500ms)

## 🔌 切换到真实 LLM

当前使用 Mock LLM(`services/llm_service.py`)。如需接入真实 LLM:

1. 安装对应 SDK:`pip install openai` 或 `pip install anthropic`
2. 修改 `llm_service.py` 的 `mock_call` 函数,调用真实 API
3. 设置环境变量 `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`

## 📊 状态机(PRD §3.4.6)

```
idle ─┬─→ requesting ─→ receiving ─→ generating ─→ completed
      │      │             │             │
      │      └─→ abnormal ←─┴─────────────┘
      ├─→ uploading ─→ validating ─→ idle
      └─→ exporting ─→ completed
```
