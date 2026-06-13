"""
/api/notifications 路由 - 系统通知。

接口列表：
  GET  /api/notifications               获取通知列表（最近50条）
  PUT  /api/notifications/{id}/read     标记单条已读
  PUT  /api/notifications/read-all      批量全部已读
  GET  /api/notifications/unread-count  获取未读数量（Navbar 角标用）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from api.auth import get_current_user
from api.schemas import NotificationListResponse, NotificationResponse
from core.database.session import get_db
from core.database.models import Notification

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """获取我的通知列表（最近50条，最新在前）。"""
    result = await db.execute(
        select(Notification)
        .where(Notification.recipient_id == current_user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifs = result.scalars().all()
    unread = sum(1 for n in notifs if not n.is_read)

    return NotificationListResponse(
        items=[
            NotificationResponse(
                notif_id=n.notif_id,
                type=n.type,
                actor_id=n.actor_id,
                payload=n.payload or {},
                is_read=n.is_read,
                created_at=n.created_at.isoformat() if n.created_at else "",
            )
            for n in notifs
        ],
        unread_count=unread,
    )


@router.put("/{notif_id}/read", status_code=204)
async def mark_read(
    notif_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """标记单条通知为已读。"""
    await db.execute(
        update(Notification)
        .where(
            Notification.notif_id == notif_id,
            Notification.recipient_id == current_user_id,
        )
        .values(is_read=True)
    )


@router.put("/read-all", status_code=204)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """批量标记所有通知为已读。"""
    await db.execute(
        update(Notification)
        .where(
            Notification.recipient_id == current_user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """获取未读通知数量（Navbar 角标专用，低开销接口）。"""
    result = await db.execute(
        select(Notification)
        .where(
            Notification.recipient_id == current_user_id,
            Notification.is_read.is_(False),
        )
    )
    count = len(result.scalars().all())
    return {"unread_count": count}
