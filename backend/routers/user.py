"""用户管理 API"""
from __future__ import annotations
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import user_service

router = APIRouter(prefix="/api/user", tags=["user"])


class UserCreate(BaseModel):
    name: str
    email: str
    role: str = "user"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: str


def _err(msg: str, code: int = 400):
    raise HTTPException(
        status_code=code,
        detail={"error_code": "BadRequest", "error_msg": msg},
    )


@router.get("/list", response_model=List[UserOut])
async def list_all():
    return user_service.list_users()


@router.post("/add", response_model=UserOut)
async def add(req: UserCreate):
    try:
        return user_service.create_user(req.name, req.email, req.role)
    except ValueError as e:
        _err(str(e))


@router.put("/{user_id}", response_model=UserOut)
async def update(user_id: str, req: UserUpdate):
    try:
        return user_service.update_user(
            user_id,
            name=req.name,
            email=req.email,
            role=req.role,
        )
    except ValueError as e:
        _err(str(e))


@router.delete("/{user_id}")
async def remove(user_id: str):
    try:
        user_service.delete_user(user_id)
    except ValueError as e:
        _err(str(e), code=404)
    return {"success": True}