"""数据集 API - 上传/列表/删除"""
from __future__ import annotations
import hashlib
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query

from config import UPLOAD_DIR, MAX_DATASET_SIZE_MB, FRIENDLY_ERRORS
from services.dataset_loader import parse_uploaded_file
from services.dataset_registry import list_datasets, get_dataset, delete_dataset

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


def _stable_id_from_bytes(content: bytes, suffix: str) -> str:
    """基于文件内容 SHA256 前 12 字符 + 格式后缀做稳定 ID
    同文件上传多次会得到同样 ID,这样重启后浏览器持有的 ID 仍然有效
    """
    h = hashlib.sha256(content).hexdigest()[:10]
    return f"ds-{h}"


@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    dataset_name: str = Form(...),
    industry_template: str = Form("通用"),
):
    """上传 CSV/Excel 文件"""
    if file.size and file.size > MAX_DATASET_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "File_TooLarge", "error_msg": FRIENDLY_ERRORS["File_TooLarge"]},
        )

    suffix = Path(file.filename or "data.csv").suffix.lower()
    if suffix not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "Dataset_FormatError", "error_msg": FRIENDLY_ERRORS["Dataset_FormatError"]},
        )

    # 先读全部内容计算稳定 ID
    content = await file.read()

    # 持久化文件(ID 来自内容 hash,而不是 uuid)
    stable_id = _stable_id_from_bytes(content, suffix)
    save_path = Path(UPLOAD_DIR) / f"{stable_id}{suffix}"
    save_path.write_bytes(content)

    # 解析 + 注册(用稳定 ID)
    try:
        info = parse_uploaded_file(save_path, dataset_name, industry_template, dataset_id_override=stable_id)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "Dataset_FormatError", "error_msg": str(e)},
        )

    return {"success": True, "data": info}


@router.get("/list")
async def list_all():
    return {"success": True, "data": list_datasets()}


@router.get("/{dataset_id}")
async def detail(dataset_id: str):
    info = get_dataset(dataset_id)
    if not info:
        raise HTTPException(status_code=404, detail={"error_code": "NotFound", "error_msg": "数据集不存在"})
    return {"success": True, "data": info}


@router.delete("/{dataset_id}")
async def remove(dataset_id: str):
    ok = delete_dataset(dataset_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"error_code": "NotFound", "error_msg": "数据集不存在"})
    return {"success": True}
