# cocoBI Demo 术语表

## 业务指标

| 内部名 | 用户友好名 | 全称 | 含义 |
|--------|----------|------|------|
| GMV | 销售额 | Gross Merchandise Value | 商品总销售额(成交总额,不含退款) |
| amount | 销售额 | Amount | 销售金额(同 GMV) |
| profit | 利润 | Profit | 扣成本后赚的钱 |
| 贡献度 | 占比 | Contribution Rate | 在归因分析中,各类目占总体的份额 |
| 维度 | 类目字段 | Dimension | 用来分组的字段(如产品类别、城市) |

## 数据集

| 内部名 | 用户友好名 | 全称 | 含义 |
|--------|----------|------|------|
| orders | 数据集(通用) | Orders | 任何上传的数据都会以 orders 命名 |
| ds-xxxx | 数据集 ID | Dataset ID | 16 字符 hex,基于文件内容 hash 生成 |

## SQL 转换(数据库字段 → 用户友好名)

| 数据库字段 | 显示名 | 数据集 |
|----------|------|--------|
| product_category | 产品类别 | sales_order |
| device_config | 设备 | user_id |
| customer_city | 城市 | sales_order |
| customer_id | 客户 | sales_order |
| is_valid | 有效 | user_id(默认过滤掉无效) |
| buy_time | 购买时间 | user_id |

## 后端开发术语

| 内部名 | 含义 |
|--------|------|
| intent | 意图分类(用户问的是哪种查询) |
| slots | 提取的参数(指标/时间/过滤条件) |
| time_range | 时间范围(开始/结束日期) |
| filters | SQL WHERE 条件 |
| schema agent | 把用户问的字段映射到数据库字段 |
| mock LLM | mock 大语言模型(实际是 regex + keyword 匹配) |
| orchestrator | 4 个 agent 串联 |

## 4 个 Agent

1. **IntentAgent** - 识别查询类型(分几类/总销售/单值/对比)
2. **SchemaAgent** - 把问的字段映射到数据集字段
3. **NL2SQLAgent** - 生成 SQL 查询
4. **StorytellingAgent** - 解读结果 + 生成图表

