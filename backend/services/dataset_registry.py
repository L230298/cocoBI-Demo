"""数据集注册表 - 内存中保存上传/示例数据集元数据"""
from __future__ import annotations
import threading
from typing import Any

_LOCK = threading.Lock()
_DATASETS: dict[str, dict[str, Any]] = {}


def register_dataset(dataset_id: str, info: dict) -> None:
    with _LOCK:
        _DATASETS[dataset_id] = info


def get_dataset(dataset_id: str) -> dict | None:
    return _DATASETS.get(dataset_id)


def list_datasets() -> list[dict]:
    return [
        {
            "dataset_id": ds_id,
            "name": ds["name"],
            "industry_template": ds.get("industry_template", "通用"),
            "row_count": ds.get("row_count", 0),
            "column_count": ds.get("column_count", 0),
            "uploaded_at": ds.get("uploaded_at", ""),
        }
        for ds_id, ds in _DATASETS.items()
    ]


def delete_dataset(dataset_id: str) -> bool:
    with _LOCK:
        return _DATASETS.pop(dataset_id, None) is not None
