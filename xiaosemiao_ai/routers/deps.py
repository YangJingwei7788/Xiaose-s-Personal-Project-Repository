"""公共依赖：数据库会话与当前登录用户"""
from typing import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from xiaosemiao_ai.config.cache_conf import cache_get, cache_set, get_user_token_key
from xiaosemiao_ai.config.db_conf import async_session_factory
from xiaosemiao_ai.config.settings import settings
from xiaosemiao_ai.crud import chat as crud_chat
from xiaosemiao_ai.crud import user as crud_user
from xiaosemiao_ai.models.chat import Chat
from xiaosemiao_ai.models.user import User
from xiaosemiao_ai.utils.security import decode_token


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """请求级数据库会话依赖"""
    async with async_session_factory() as session:
        yield session


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    """JWT 鉴权：校验请求头 Authorization 中的登录令牌"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    token = authorization.removeprefix("Bearer ").strip()
    user_id = decode_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="无效的登录令牌")

    # 优先校验 Redis 登录令牌缓存，减少数据库查询
    cached_token = await cache_get(get_user_token_key(user_id))
    if cached_token is not None:
        if cached_token != token:
            raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    else:
        db_token = await crud_user.get_user_token(db, user_id, token)
        if db_token is None:
            raise HTTPException(status_code=401, detail="无效的登录令牌")
        # Redis 不可用/缺失时回源数据库校验，并回填缓存
        await cache_set(get_user_token_key(user_id), token, ttl=settings.JWT_EXPIRE_DAYS * 24 * 3600)

    user = await crud_user.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


async def get_owned_chat(db: AsyncSession, user_id: int, chat_id: int) -> Chat:
    """校验对话存在且属于当前用户，否则返回 404"""
    chat = await crud_chat.get_chat(db, chat_id)
    if chat is None or chat.user_id != user_id:
        raise HTTPException(status_code=404, detail="对话不存在")
    return chat