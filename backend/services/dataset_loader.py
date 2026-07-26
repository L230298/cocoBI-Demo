"""数据集加载器 - 将 CSV/Excel 加载到 SQLite 内存数据库"""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd

from config import UPLOAD_DIR


def load_dataset_to_sqlite(conn: sqlite3.Connection, dataset_id: str) -> None:
    """根据 dataset_id 找到文件并加载到 SQLite"""
    from .dataset_registry import get_dataset

    info = get_dataset(dataset_id)
    if not info:
        raise ValueError(f"dataset {dataset_id} not found")

    file_path = Path(info["file_path"])
    if not file_path.exists():
        raise FileNotFoundError(f"file {file_path} not found")

    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)
    else:  # xlsx / xls
        df = pd.read_excel(file_path)

    # 列名清洗:去掉前后空格、替换特殊字符
    df.columns = [c.strip().replace(" ", "_").replace("-", "_") for c in df.columns]

    # 日期列尽量解析
    for col in df.columns:
        if "date" in col.lower() or "时间" in col or "日期" in col:
            try:
                df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
            except Exception:
                pass

    df.to_sql("orders", conn, if_exists="replace", index=False)


def parse_uploaded_file(file_path: Path, dataset_name: str, industry_template: str = "通用", dataset_id_override: str | None = None) -> dict:
    """解析上传文件,提取 Schema 与样本,写入数据集注册表"""
    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path, nrows=1000)  # 抽样前 1000 行分析 Schema
    else:
        df = pd.read_excel(file_path, nrows=1000)

    df.columns = [c.strip() for c in df.columns]
    fields = []
    for col in df.columns:
        sample = df[col].dropna().head(1).tolist()
        fields.append(
            {
                "name": col,
                "type": str(df[col].dtype),
                "sample": sample[0] if sample else None,
            }
        )

    # 完整行数
    if file_path.suffix.lower() == ".csv":
        total_rows = sum(1 for _ in open(file_path, encoding="utf-8", errors="ignore")) - 1
    else:
        full_df = pd.read_excel(file_path)
        total_rows = len(full_df)

    # 推断业务术语
    glossary = _infer_glossary(df)

    from datetime import datetime
    import uuid

    # 优先用稳定 ID(从文件 hash),保证重启后 ID 不变
    if dataset_id_override:
        dataset_id = dataset_id_override
    else:
        dataset_id = f"ds-{uuid.uuid4().hex[:8]}"
    info = {
        "dataset_id": dataset_id,
        "name": dataset_name,
        "industry_template": industry_template,
        "file_path": str(file_path),
        "fields": fields,
        "row_count": total_rows,
        "column_count": len(df.columns),
        "size_bytes": file_path.stat().st_size,
        "business_glossary": glossary,
        "uploaded_at": datetime.utcnow().isoformat(),
    }

    from .dataset_registry import register_dataset

    register_dataset(dataset_id, info)
    return info


def load_existing_uploads():
    """启动时扫描 uploads 目录,重新注册已有数据集
    Volume 挂载后,/app/data/uploads 里的文件还在,需要重新注册到内存
    """
    from config import UPLOAD_DIR
    from pathlib import Path
    import logging
    logger = logging.getLogger(__name__)

    p = Path(UPLOAD_DIR)
    if not p.exists():
        logger.info("uploads 目录不存在,跳过自动加载")
        return

    loaded = 0
    for f in p.iterdir():
        if f.suffix.lower() not in (".csv", ".xlsx", ".xls"):
            continue
        # file format: ds-<hash>.csv
        dataset_id = f.stem  # ds-xxxxxxxxxx
        try:
            info = parse_uploaded_file(f, dataset_name=f.stem, industry_template="通用", dataset_id_override=dataset_id)
            loaded += 1
            logger.info(f"自动加载已上传数据集: {dataset_id} ({info['row_count']} 行)")
        except Exception as e:
            logger.warning(f"加载 {f.name} 失败: {e}")

    logger.info(f"启动自动加载完成,共 {loaded} 个数据集")


def _infer_glossary(df) -> dict[str, str]:
    """基于列名推断业务术语映射"""
    glossary = {}
    cols_lower = {c.lower(): c for c in df.columns}
    if "status" in cols_lower or "order_status" in cols_lower or "状态" in cols_lower:
        status_col = cols_lower.get("order_status") or cols_lower.get("status") or "状态"
        if status_col in df.columns:
            valid_vals = df[status_col].dropna().unique().tolist()[:3]
            if valid_vals:
                glossary["有效订单"] = f"`{status_col}` IN ({', '.join(repr(v) for v in valid_vals)})"
    return glossary
