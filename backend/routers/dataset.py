"""数据集 API - 上传/列表/删除"""
from __future__ import annotations
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query

from config import UPLOAD_DIR, MAX_DATASET_SIZE_MB, FRIENDLY_ERRORS
from services.dataset_loader import parse_uploaded_file
from services.dataset_registry import list_datasets, get_dataset, delete_dataset

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


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

    # 持久化文件
    file_id = uuid.uuid4().hex[:12]
    save_path = Path(UPLOAD_DIR) / f"{file_id}{suffix}"
    content = await file.read()
    save_path.write_bytes(content)

    # 解析 + 注册
    try:
        info = parse_uploaded_file(save_path, dataset_name, industry_template)
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
