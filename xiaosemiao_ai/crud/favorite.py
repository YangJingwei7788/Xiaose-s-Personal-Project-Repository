"""素材收藏相关数据库操作"""
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from xiaosemiao_ai.models.chat import Chat
from xiaosemiao_ai.models.favorite import Favorite


async def add_favorite(db: AsyncSession, user_id: int, chat_id: int) -> Favorite:
    favorite = Favorite(user_id=user_id, chat_id=chat_id)
    db.add(favorite)
    try:
        await db.commit()
        await db.refresh(favorite)
        return favorite
    except IntegrityError:
        await db.rollback()
        raise ValueError("该对话已收藏")


async def remove_favorite(db: AsyncSession, user_id: int, chat_id: int) -> bool:
    favorite = await db.scalar(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.chat_id == chat_id)
    )
    if favorite is None:
        return False
    await db.delete(favorite)
    await db.commit()
    return True


async def check_favorite(db: AsyncSession, user_id: int, chat_id: int) -> bool:
    favorite_id = await db.scalar(
        select(Favorite.id).where(Favorite.user_id == user_id, Favorite.chat_id == chat_id)
    )
    return favorite_id is not None


async def list_favorites(db: AsyncSession, user_id: int, page: int, size: int) -> tuple[int, list[Chat]]:
    base = (
        select(Chat)
        .join(Favorite, Favorite.chat_id == Chat.id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc(), Chat.id.desc())
    )
    total = (await db.scalar(select(func.count()).select_from(base.order_by(None).subquery()))) or 0
    chats = list((await db.scalars(base.offset((page - 1) * size).limit(size))).all())
    return total, chats


async def clear_favorites(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(delete(Favorite).where(Favorite.user_id == user_id))
    await db.commit()
    return result.rowcount or 0