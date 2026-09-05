"""素材收藏、取消收藏、收藏列表接口"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from xiaosemiao_ai.config.cache_conf import (
    cache_get_json,
    cache_set_json,
    get_favorite_list_key,
    invalidate_user_favorite_caches,
)
from xiaosemiao_ai.config.settings import settings
from xiaosemiao_ai.crud import favorite as crud_favorite
from xiaosemiao_ai.models.user import User
from xiaosemiao_ai.routers.deps import get_current_user, get_db, get_owned_chat
from xiaosemiao_ai.schemas.chat import ChatListItem
from xiaosemiao_ai.schemas.favorite import FavoriteAddRequest
from xiaosemiao_ai.utils.common import page_data, success

router = APIRouter()


@router.get("/check", summary="检查指定对话是否已收藏")
async def check_favorite(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    favorited = await crud_favorite.check_favorite(db, user.id, chat_id)
    return success({"chat_id": chat_id, "favorited": favorited})


@router.post("/add", summary="收藏对话会话")
async def add_favorite(
    payload: FavoriteAddRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_chat(db, user.id, payload.chat_id)
    try:
        await crud_favorite.add_favorite(db, user.id, payload.chat_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await invalidate_user_favorite_caches(user.id)
    return success({"chat_id": payload.chat_id}, "收藏成功")


@router.delete("/remove", summary="取消对话收藏")
async def remove_favorite(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    removed = await crud_favorite.remove_favorite(db, user.id, chat_id)
    if not removed:
        raise HTTPException(status_code=404, detail="收藏不存在")
    await invalidate_user_favorite_caches(user.id)
    return success({"chat_id": chat_id}, "取消收藏成功")


@router.get("/list", summary="获取个人收藏列表（分页）")
async def list_favorites(
    page: int = 1,
    size: int = 10,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    size = min(max(1, size), 100)
    cache_key = get_favorite_list_key(user.id, page, size)
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return success(cached)
    total, chats = await crud_favorite.list_favorites(db, user.id, page, size)
    items = [ChatListItem.model_validate(c).model_dump(mode="json") for c in chats]
    data = page_data(total, page, size, items)
    await cache_set_json(cache_key, data, ttl=settings.CACHE_FAVORITE_LIST_TTL)
    return success(data)


@router.delete("/clear", summary="清空所有收藏")
async def clear_favorites(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cleared = await crud_favorite.clear_favorites(db, user.id)
    await invalidate_user_favorite_caches(user.id)
    return success({"cleared": cleared}, "已清空收藏")