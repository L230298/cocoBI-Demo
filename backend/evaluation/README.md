# cocoBI 评测集 — P1 迭代交付

> 来源：P1 迭代建议「评测集分级管理」
> 创建日期：2026-08-04
> 节奏（PRD §3.6.3）：周更核心 / 月更边界 / 版本发布前全量回归

## 目录结构

```
evaluation/
├── README.md                  (本文件)
├── intent/
│   ├── core/                  5 个核心意图各 ≥ 10 条 (Easy/Medium)
│   │   ├── i1_basic.jsonl     (基础问数)
│   │   ├── i2_compare_topn.jsonl
│   │   ├── i3_threshold.jsonl
│   │   ├── i4_attribution.jsonl
│   │   └── i5_interpretation.jsonl
│   └── edge/                  边界 (Unknown / Chitchat / 越界)
│       └── unknown.jsonl
├── nl2sql/
│   ├── easy/    nl2sql_easy.jsonl      (单表简单查询)
│   ├── medium/  nl2sql_medium.jsonl    (多表 JOIN / 聚合)
│   ├── hard/    nl2sql_hard.jsonl      (复杂业务逻辑)
│   └── edge/    nl2sql_edge.jsonl      (空值 / 特殊值 / 注入风险)
├── attribution/
│   ├── standard/  attr_standard.jsonl  (标准归因)
│   └── edge/      attr_edge.jsonl      (极端分布 / 无显著因素)
├── interpretation/
│   ├── standard/      interp_standard.jsonl
│   └── hallucination/ interp_hallucination.jsonl (幻觉检测)
├── by_industry/
│   ├── retail/          retail_queries.jsonl
│   ├── ecommerce/       ecommerce_queries.jsonl
│   ├── manufacturing/   manufacturing_queries.jsonl
│   └── education/       education_queries.jsonl
└── regression/
    └── badcase_regression.jsonl        (回归 BC-001~004 + 新发现的)
```

## JSONL Schema

每行一条 query，字段：
```json
{
  "qid": "I1-001",
  "intent": "QueryBasicMetrics",
  "industry": "通用",
  "difficulty": "easy",
  "user_input": "上周 GMV 是多少?",
  "expected": {
    "must_contain_sql_keywords": ["SUM", "amount", "order_date"],
    "must_contain_terms": ["GMV"],
    "must_NOT_contain": ["DROP", "DELETE"]
  },
  "tags": ["业务术语", "时间范围"]
}
```

## 数据来源

- `badcase_regression.jsonl` 收录 BC-2026-001~004
- 各 intent core 目录首批 10 条由 `run_eval_queries.py` 改编 + 手工补充
- by_industry 目录复用通用集 + 行业术语替换

## 运行评测

```bash
# 跑全部
python evaluation/run_eval.py

# 只跑核心意图
python evaluation/run_eval.py --filter intent/core

# 只跑回归集
python evaluation/run_eval.py --filter regression
```