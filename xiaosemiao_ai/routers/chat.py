"""AI 问答、历史会话查询接口"""
import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from xiaosemiao_ai.config.cache_conf import (
    cache_delete,
    cache_delete_pattern,
    cache_get_json,
    cache_set_json,
    get_chat_context_key,
    get_chat_detail_key,
    get_chat_list_key,
    get_history_list_key,
    invalidate_user_chat_caches,
)
from xiaosemiao_ai.config.db_conf import async_session_factory
from xiaosemiao_ai.config.settings import settings
from xiaosemiao_ai.crud import chat as crud_chat
from xiaosemiao_ai.models.user import User
from xiaosemiao_ai.routers.deps import get_current_user, get_db, get_owned_chat
from xiaosemiao_ai.schemas.chat import (
    ChatCreate,
    ChatDetailOut,
    ChatListItem,
    ChatMessageOut,
    ChatRoleUpdate,
    ChatSendRequest,
    ChatTitleUpdate,
)
from xiaosemiao_ai.utils.common import page_data, success
from xiaosemiao_ai.utils.llm_client import stream_chat

logger = logging.getLogger(__name__)

router = APIRouter()


def _sse(data: dict) -> str:
    """SSE 事件帧"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _truncate_title(text: str, max_len: int = 30) -> str:
    """兜底标题：把首条消息压缩成简洁标题"""
    text = " ".join(text.split())
    if not text:
        return "新对话"
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


async def _generate_title(
    user_message: str,
    assistant_message: str,
    *,
    provider: str = "public",
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    """调用大模型根据首轮问答生成简洁标题；失败时回退为首条消息截断"""
    try:
        prompt = (
            "你是标题生成助手。请根据下面的第一轮对话，用一句话概括主题，"
            "生成一个简洁的中文标题（20字以内），只输出标题本身，不要引号、不要多余文字。\n"
            f"用户问：{user_message[:200]}\nAI答：{assistant_message[:200]}"
        )

        async def _collect() -> str:
            title = ""
            async for delta in stream_chat(
                [{"role": "user", "content": prompt}],
                provider=provider,
                base_url=base_url,
                api_key=api_key,
                model=model,
            ):
                title += delta
            return title

        title = await asyncio.wait_for(_collect(), timeout=15)
        title = title.strip().strip('"').strip("'").strip("“").strip("”")
        title = " ".join(title.split())
        if title:
            return title[:30]
    except Exception as exc:
        logger.warning("自动生成标题失败，使用兜底标题: %s", exc)
    return _truncate_title(user_message)


def _resolve_provider(user: User, payload: ChatSendRequest) -> tuple[str, str | None, str | None, str | None]:
    """确定本次提问使用的大模型来源：public / local / deepseek"""
    provider = (payload.provider or user.llm_provider or "public").strip().lower()
    base_url = payload.base_url or user.llm_base_url
    api_key = payload.api_key or user.llm_api_key
    if provider == "public":
        # 公共 API 使用服务端默认模型，也可临时指定模型名
        model = payload.model
    else:
        model = payload.model or user.llm_model
    return provider, base_url, api_key, model


async def _load_context(db: AsyncSession, chat_id: int) -> list[dict]:
    """读取对话上下文：优先 Redis 缓存 chat:context:{chat_id}，否则查库"""
    cache_key = get_chat_context_key(chat_id)
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return cached
    messages = await crud_chat.get_recent_messages(db, chat_id, limit=settings.CONTEXT_MESSAGE_COUNT)
    context = [{"role": m.role, "content": m.content} for m in messages]
    await cache_set_json(cache_key, context, ttl=settings.CACHE_CHAT_CONTEXT_TTL)
    return context


@router.post("/create", summary="创建空白对话会话")
async def create_chat(
    payload: ChatCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat = await crud_chat.create_chat(db, user.id, title=payload.title)
    return success({"chat_id": chat.id, "title": chat.title}, "创建成功")


@router.get("/list", summary="获取对话列表（分页）")
async def list_chats(
    page: int = 1,
    size: int = 10,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    size = min(max(1, size), 100)
    cache_key = get_chat_list_key(user.id, page, size)
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return success(cached)
    total, chats = await crud_chat.list_chats(db, user.id, page, size)
    items = [ChatListItem.model_validate(c).model_dump(mode="json") for c in chats]
    data = page_data(total, page, size, items)
    await cache_set_json(cache_key, data, ttl=settings.CACHE_CHAT_LIST_TTL)
    return success(data)


@router.get("/detail", summary="查询单条对话完整详情")
async def chat_detail(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cache_key = get_chat_detail_key(chat_id)
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return success(cached)
    chat = await get_owned_chat(db, user.id, chat_id)
    messages = await crud_chat.get_chat_messages(db, chat_id)
    data = ChatDetailOut(
        id=chat.id,
        title=chat.title,
        system_prompt=chat.system_prompt,
        created_at=chat.created_at,
        messages=[ChatMessageOut.model_validate(m) for m in messages],
    ).model_dump(mode="json")
    await cache_set_json(cache_key, data, ttl=settings.CACHE_CHAT_DETAIL_TTL)
    return success(data)


@router.delete("/delete", summary="删除指定对话会话")
async def delete_chat(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat = await get_owned_chat(db, user.id, chat_id)
    await crud_chat.delete_chat(db, chat)
    await invalidate_user_chat_caches(user.id, chat_id)
    return success(message="删除成功")


@router.delete("/clear", summary="清空当前用户全部对话")
async def clear_chats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat_ids = await crud_chat.list_chat_ids(db, user.id)
    cleared = await crud_chat.clear_chats(db, user.id)
    for cid in chat_ids:
        await cache_delete(get_chat_detail_key(cid))
        await cache_delete(get_chat_context_key(cid))
    await cache_delete_pattern(f"chat:list:{user.id}:*")
    await cache_delete_pattern(f"favorite:list:{user.id}:*")
    await cache_delete(get_history_list_key(user.id))
    return success({"cleared": cleared}, "已清空全部对话")


@router.put("/title", summary="修改对话会话标题")
async def update_title(
    chat_id: int,
    payload: ChatTitleUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_chat(db, user.id, chat_id)
    await crud_chat.update_chat_title(db, chat_id, payload.title)
    await cache_delete(get_chat_detail_key(chat_id))
    await invalidate_user_chat_caches(user.id, chat_id)
    return success({"chat_id": chat_id, "title": payload.title}, "标题修改成功")


@router.put("/role", summary="修改会话角色设定")
async def update_role(
    chat_id: int,
    payload: ChatRoleUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_chat(db, user.id, chat_id)
    await crud_chat.update_chat_system_prompt(db, chat_id, payload.system_prompt)
    await cache_delete(get_chat_detail_key(chat_id))
    await cache_delete(get_chat_context_key(chat_id))
    await invalidate_user_chat_caches(user.id, chat_id)
    return success({"chat_id": chat_id, "system_prompt": payload.system_prompt}, "角色设定已保存")


@router.post("/send", summary="发送提问（流式返回 AI 回复）")
async def send_message(
    payload: ChatSendRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_new_chat = payload.chat_id is None
    if payload.chat_id:
        chat = await get_owned_chat(db, user.id, payload.chat_id)
    else:
        chat = await crud_chat.create_chat(db, user.id)

    # 确定本次提问使用哪个大模型来源与参数
    provider, base_url, api_key, model = _resolve_provider(user, payload)

    context = await _load_context(db, chat.id)
    if chat.system_prompt:
        context.insert(0, {"role": "system", "content": chat.system_prompt})
    context.append({"role": "user", "content": payload.message})

    async def event_stream() -> AsyncGenerator[str, None]:
        full_text = ""
        try:
            async for delta in stream_chat(
                context,
                provider=provider,
                base_url=base_url,
                api_key=api_key,
                model=model,
            ):
                full_text += delta
                yield _sse({"type": "delta", "content": delta})
        except Exception as exc:
            yield _sse({"type": "error", "message": f"模型调用失败：{exc}"})
            return

        # 流式结束后持久化消息并失效相关缓存
        final_title = None
        async with async_session_factory() as session:
            await crud_chat.add_message(session, chat.id, "user", payload.message)
            await crud_chat.add_message(session, chat.id, "assistant", full_text)
            if is_new_chat:
                # 新对话：根据首轮问答自动生成更准确的标题
                final_title = await _generate_title(
                    payload.message,
                    full_text,
                    provider=provider,
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                )
                await crud_chat.update_chat_title(session, chat.id, final_title)
            await crud_chat.touch_chat(session, chat.id)
            await invalidate_user_chat_caches(user.id, chat.id)

        yield _sse({"type": "done", "chat_id": chat.id, "content": full_text, "title": final_title})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )