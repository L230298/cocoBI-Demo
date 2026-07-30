"""用户管理 service - SQLite 持久化"""
from __future__ import annotations
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path

from config import DATA_DIR

_DB_PATH = Path(DATA_DIR) / "users.db"
_LOCK = threading.Lock()

ALLOWED_ROLES = {"admin", "user"}


def _init_db() -> None:
    """初始化表结构"""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


_init_db()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def list_users() -> list[dict]:
    with _LOCK, _conn() as conn:
        rows = conn.execute(
            "SELECT id, name, email, role, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_user(user_id: str) -> dict | None:
    with _LOCK, _conn() as conn:
        row = conn.execute(
            "SELECT id, name, email, role, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def create_user(name: str, email: str, role: str = "user") -> dict:
    name = (name or "").strip()
    email = (email or "").strip()
    role = (role or "user").strip()
    if not name:
        raise ValueError("用户名不能为空")
    if not email or "@" not in email:
        raise ValueError("邮箱格式不正确")
    if role not in ALLOWED_ROLES:
        raise ValueError(f"角色必须是 {ALLOWED_ROLES} 之一")

    user_id = f"u-{uuid.uuid4().hex[:8]}"
    created_at = datetime.utcnow().isoformat()
    with _LOCK, _conn() as conn:
        try:
            conn.execute(
                "INSERT INTO users (id, name, email, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, name, email, role, created_at),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"邮箱 {email} 已被使用")
    return {
        "id": user_id,
        "name": name,
        "email": email,
        "role": role,
        "created_at": created_at,
    }


def update_user(user_id: str, *, name: str | None = None, email: str | None = None, role: str | None = None) -> dict:
    existing = get_user(user_id)
    if not existing:
        raise ValueError(f"用户 {user_id} 不存在")

    new_name = (name if name is not None else existing["name"]).strip()
    new_email = (email if email is not None else existing["email"]).strip()
    new_role = (role if role is not None else existing["role"]).strip()

    if not new_name:
        raise ValueError("用户名不能为空")
    if "@" not in new_email:
        raise ValueError("邮箱格式不正确")
    if new_role not in ALLOWED_ROLES:
        raise ValueError(f"角色必须是 {ALLOWED_ROLES} 之一")

    with _LOCK, _conn() as conn:
        try:
            conn.execute(
                "UPDATE users SET name = ?, email = ?, role = ? WHERE id = ?",
                (new_name, new_email, new_role, user_id),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"邮箱 {new_email} 已被使用")
    return get_user(user_id)


def delete_user(user_id: str) -> None:
    with _LOCK, _conn() as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"用户 {user_id} 不存在")