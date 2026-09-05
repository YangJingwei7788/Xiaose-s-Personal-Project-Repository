"""用户账号相关数据库操作"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xiaosemiao_ai.models.user import User, UserToken
from xiaosemiao_ai.utils.security import hash_password


async def create_user(db: AsyncSession, username: str, password: str, nickname: str = "") -> User:
    user = User(username=username, password=hash_password(password), nickname=nickname or username)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    return await db.scalar(select(User).where(User.username == username))


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def update_user(db: AsyncSession, user: User, nickname: str | None = None, avatar: str | None = None) -> User:
    if nickname is not None:
        user.nickname = nickname
    if avatar is not None:
        user.avatar = avatar
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_password(db: AsyncSession, user: User, new_password: str) -> None:
    user.password = hash_password(new_password)
    await db.commit()


async def update_user_llm_settings(
    db: AsyncSession,
    user: User,
    *,
    provider: str | None,
    base_url: str | None,
    api_key: str | None,
    model: str | None,
) -> User:
    """保存用户大模型设置（空值存为 NULL）"""
    user.llm_provider = provider or None
    user.llm_base_url = base_url or None
    user.llm_api_key = api_key or None
    user.llm_model = model or None
    await db.commit()
    await db.refresh(user)
    return user


async def create_user_token(db: AsyncSession, user_id: int, token: str, expires_at: datetime) -> UserToken:
    user_token = UserToken(user_id=user_id, token=token, expires_at=expires_at)
    db.add(user_token)
    await db.commit()
    return user_token


async def get_user_token(db: AsyncSession, user_id: int, token: str) -> UserToken | None:
    return await db.scalar(
        select(UserToken).where(
            UserToken.user_id == user_id,
            UserToken.token == token,
            UserToken.expires_at > datetime.now(),
        )
    )


async def delete_user_token(db: AsyncSession, user_id: int, token: str) -> None:
    user_token = await db.scalar(
        select(UserToken).where(UserToken.user_id == user_id, UserToken.token == token)
    )
    if user_token is not None:
        await db.delete(user_token)
        await db.commit()