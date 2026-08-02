# 线上测试数据采集汇总

采集时间: 2026-08-02
来源: https://cocobi-demo-production.up.railway.app

## 1. 服务健康

- `/api/health` 返回 `{"status":"ok"}`

## 2. 注册工具数: 7

- **execute_sql** -- 
- **get_data_source_metadata** -- 
- **render_chart** -- 
- **export_data_story** -- 
- **get_recent_queries** -- 
- **collect_user_feedback** -- 
- **generate_next_steps** -- 

## 3. 数据集数: 8 (累计 242 行)

| ID | 行业模板 | 行数 | 列数 | 上传时间 |
|---|---|---|---|---|
| `eddebb55059a` | 通用 | 60 | 6 | 2026-07-30T08:56:27 |
| `d1d33e56969e` | 通用 | 60 | 6 | 2026-07-30T08:56:27 |
| `ds-aeac74e799` | 通用 | 3 | 3 | 2026-07-30T08:56:27 |
| `ds-1ef97a5720` | 通用 | 40 | 10 | 2026-07-30T08:56:27 |
| `ds-a6d37f31c7` | 通用 | 1 | 4 | 2026-07-30T08:56:27 |
| `ds-c7f849859e` | 通用 | 5 | 3 | 2026-07-30T08:56:27 |
| `ds-aa68858078` | 通用 | 13 | 6 | 2026-07-30T08:56:27 |
| `ds-de555b2183` | 通用 | 60 | 6 | 2026-07-30T08:56:28 |

## 4. 用户数: 3

| ID | 用户名 | 邮箱 | 角色 | 创建时间 |
|---|---|---|---|---|
| `u-138bd344` | L | 888@qq.com | user | 2026-07-30T08:42:06 |
| `u-6747f50e` | 李四 | li@example.com | user | 2026-07-30T08:28:19 |
| `u-bf922b0c` | 测试用户 | test@example.com | admin | 2026-07-30T08:27:23 |

## 5. 应用日志

- 文件: app.log (1060 字节, 10 行)

最近 5 条:

```
2026-07-30 08:56:27,946 [INFO] services.dataset_loader: 自动加载已上传数据集: ds-a6d37f31c7 (1 行)
2026-07-30 08:56:27,947 [INFO] services.dataset_loader: 自动加载已上传数据集: ds-c7f849859e (5 行)
2026-07-30 08:56:27,979 [INFO] services.dataset_loader: 自动加载已上传数据集: ds-aa68858078 (13 行)
2026-07-30 08:56:28,016 [INFO] services.dataset_loader: 自动加载已上传数据集: ds-de555b2183 (60 行)
2026-07-30 08:56:28,017 [INFO] services.dataset_loader: 启动自动加载完成,共 8 个数据集
```

## 6. 日志下载接口验证

- `/api/log/list` -- 列出日志文件 (含轮转历史), 200 OK
- `/api/log/download` -- 下载当前 app.log, 200 OK, Content-Type: text/plain, attachment
- `/log/download` (无 /api 前缀) -- 错误路由, 返回前端 SPA HTML