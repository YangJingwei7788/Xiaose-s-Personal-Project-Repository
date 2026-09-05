"""浏览历史相关数据库操作"""
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xiaosemiao_ai.models.chat import Chat
from xiaosemiao_ai.models.history import History


async def add_history(db: AsyncSession, user_id: int, chat_id: int) -> History:
    history = await db.scalar(
        select(History).where(History.user_id == user_id, History.chat_id == chat_id)
    )
    if history is None:
        history = History(user_id=user_id, chat_id=chat_id, last_viewed_at=datetime.now())
        db.add(history)
    else:
        history.last_viewed_at = datetime.now()
    await db.commit()
    await db.refresh(history)
    return history


async def list_all_history(db: AsyncSession, user_id: int) -> list[Chat]:
    stmt = (
        select(Chat)
        .join(History, History.chat_id == Chat.id)
        .where(History.user_id == user_id)
        .order_by(History.last_viewed_at.desc(), Chat.id.desc())
    )
    return list((await db.scalars(stmt)).all())


async def list_history(db: AsyncSession, user_id: int, page: int, size: int) -> tuple[int, list[Chat]]:
    base = (
        select(Chat)
        .join(History, History.chat_id == Chat.id)
        .where(History.user_id == user_id)
        .order_by(History.last_viewed_at.desc(), Chat.id.desc())
    )
    total = (await db.scalar(select(func.count()).select_from(base.order_by(None).subquery()))) or 0
    chats = list((await db.scalars(base.offset((page - 1) * size).limit(size))).all())
    return total, chats


async def delete_history(db: AsyncSession, user_id: int, chat_id: int) -> bool:
    history = await db.scalar(
        select(History).where(History.user_id == user_id, History.chat_id == chat_id)
    )
    if history is None:
        return False
    await db.delete(history)
    await db.commit()
    return True


async def clear_history(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(delete(History).where(History.user_id == user_id))
    await db.commit()
    return result.rowcount or 0