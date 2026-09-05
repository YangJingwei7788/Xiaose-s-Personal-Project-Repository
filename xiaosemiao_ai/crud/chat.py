"""AI 对话会话相关数据库操作"""
from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from xiaosemiao_ai.models.chat import Chat, ChatMessage
from xiaosemiao_ai.models.favorite import Favorite
from xiaosemiao_ai.models.history import History

DEFAULT_TITLE = "新对话"


async def create_chat(db: AsyncSession, user_id: int, title: str | None = None) -> Chat:
    chat = Chat(user_id=user_id, title=title or DEFAULT_TITLE)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat


async def get_chat(db: AsyncSession, chat_id: int) -> Chat | None:
    return await db.get(Chat, chat_id)


async def get_chat_messages(db: AsyncSession, chat_id: int) -> list[ChatMessage]:
    stmt = select(ChatMessage).where(ChatMessage.chat_id == chat_id).order_by(ChatMessage.id)
    return list((await db.scalars(stmt)).all())


async def get_recent_messages(db: AsyncSession, chat_id: int, limit: int = 20) -> list[ChatMessage]:
    """按时间倒序取最近 limit 条消息，再反转回正序"""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
    )
    rows = list((await db.scalars(stmt)).all())
    rows.reverse()
    return rows


async def list_chats(db: AsyncSession, user_id: int, page: int, size: int) -> tuple[int, list[Chat]]:
    base = select(Chat).where(Chat.user_id == user_id).order_by(Chat.updated_at.desc(), Chat.id.desc())
    total = (await db.scalar(select(func.count()).select_from(base.order_by(None).subquery()))) or 0
    chats = list((await db.scalars(base.offset((page - 1) * size).limit(size))).all())
    return total, chats


async def list_chat_ids(db: AsyncSession, user_id: int) -> list[int]:
    """返回当前用户全部对话 ID"""
    return list((await db.scalars(select(Chat.id).where(Chat.user_id == user_id))).all())


async def clear_chats(db: AsyncSession, user_id: int) -> int:
    """清空当前用户全部对话（同时清理关联消息、收藏、浏览记录）"""
    ids = await list_chat_ids(db, user_id)
    if not ids:
        return 0
    await db.execute(delete(ChatMessage).where(ChatMessage.chat_id.in_(ids)))
    await db.execute(delete(Favorite).where(Favorite.chat_id.in_(ids)))
    await db.execute(delete(History).where(History.chat_id.in_(ids)))
    result = await db.execute(delete(Chat).where(Chat.id.in_(ids)))
    await db.commit()
    return result.rowcount or 0


async def update_chat_title(db: AsyncSession, chat_id: int, title: str) -> None:
    await db.execute(update(Chat).where(Chat.id == chat_id).values(title=title))
    await db.commit()


async def update_chat_system_prompt(db: AsyncSession, chat_id: int, system_prompt: str) -> None:
    """更新会话角色设定（空字符串存为 NULL）"""
    await db.execute(update(Chat).where(Chat.id == chat_id).values(system_prompt=system_prompt or None))
    await db.commit()


async def touch_chat(db: AsyncSession, chat_id: int) -> None:
    """刷新对话更新时间，用于列表排序"""
    await db.execute(update(Chat).where(Chat.id == chat_id).values(updated_at=datetime.now()))
    await db.commit()


async def add_message(db: AsyncSession, chat_id: int, role: str, content: str) -> ChatMessage:
    message = ChatMessage(chat_id=chat_id, role=role, content=content)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def delete_chat(db: AsyncSession, chat: Chat) -> None:
    await db.delete(chat)
    await db.commit()