
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import get_current_user
from app.modules.auth.models import User
from app.modules.logs.models import AppLog

router = APIRouter()


class LogEntry(BaseModel):
    id: str
    level: str
    title: str
    message: str
    traceback: str | None = None
    module: str | None = None
    request_path: str | None = None
    request_method: str | None = None
    user_id: str | None = None
    extra: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


async def _require_admin(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()
    if not user or user.email not in settings.ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("", response_model=list[LogEntry], include_in_schema=False)
async def list_logs(
    level: str | None = Query(None),
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
) -> list[AppLog]:
    q = select(AppLog).order_by(AppLog.created_at.desc()).limit(limit)
    if level:
        q = q.where(AppLog.level == level.upper())
    result = await db.execute(q)
    return list(result.scalars().all())


@router.delete("/{log_id}", include_in_schema=False)
async def delete_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
) -> dict:
    await db.execute(delete(AppLog).where(AppLog.id == log_id))
    await db.commit()
    return {"ok": True}


@router.delete("", include_in_schema=False)
async def clear_all_logs(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
) -> dict:
    await db.execute(delete(AppLog))
    await db.commit()
    return {"ok": True}
