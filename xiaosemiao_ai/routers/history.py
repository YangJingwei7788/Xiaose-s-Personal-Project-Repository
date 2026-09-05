"""浏览历史相关接口"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from xiaosemiao_ai.config.cache_conf import (
    cache_get_json,
    cache_set_json,
    get_history_list_key,
    invalidate_user_history_cache,
)
from xiaosemiao_ai.config.settings import settings
from xiaosemiao_ai.crud import history as crud_history
from xiaosemiao_ai.models.user import User
from xiaosemiao_ai.routers.deps import get_current_user, get_db, get_owned_chat
from xiaosemiao_ai.schemas.chat import ChatListItem
from xiaosemiao_ai.schemas.history import HistoryAddRequest
from xiaosemiao_ai.utils.common import page_data, success

router = APIRouter()


@router.post("/add", summary="新增对话浏览记录")
async def add_history(
    payload: HistoryAddRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_chat(db, user.id, payload.chat_id)
    await crud_history.add_history(db, user.id, payload.chat_id)
    await invalidate_user_history_cache(user.id)
    return success({"chat_id": payload.chat_id}, "已记录浏览")


@router.get("/list", summary="浏览历史列表获取（分页）")
async def list_history(
    page: int = 1,
    size: int = 10,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    size = min(max(1, size), 100)
    # 历史列表整体缓存于 history:list:{user_id}，命中后在内存分页
    cache_key = get_history_list_key(user.id)
    cached = await cache_get_json(cache_key)
    if cached is not None:
        start = (page - 1) * size
        return success(page_data(len(cached), page, size, cached[start : start + size]))
    chats = await crud_history.list_all_history(db, user.id)
    items = [ChatListItem.model_validate(c).model_dump(mode="json") for c in chats]
    await cache_set_json(cache_key, items, ttl=settings.CACHE_HISTORY_LIST_TTL)
    start = (page - 1) * size
    return success(page_data(len(items), page, size, items[start : start + size]))


@router.delete("/delete", summary="删除单条浏览记录")
async def delete_history(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    removed = await crud_history.delete_history(db, user.id, chat_id)
    if not removed:
        raise HTTPException(status_code=404, detail="浏览记录不存在")
    await invalidate_user_history_cache(user.id)
    return success({"chat_id": chat_id}, "删除成功")


@router.delete("/clear", summary="清空浏览历史")
async def clear_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cleared = await crud_history.clear_history(db, user.id)
    await invalidate_user_history_cache(user.id)
    return success({"cleared": cleared}, "已清空浏览历史")