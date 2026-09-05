"""Redis 缓存配置与缓存操作封装（统一封装便于业务调用）"""
import json
import logging
import time
from typing import Any

import redis.asyncio as aioredis

from xiaosemiao_ai.config.settings import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None
_redis_down_until: float = 0.0  # 熔断截止时间（time.monotonic() 秒）

REDIS_FAIL_COOLDOWN: float = 30.0   # Redis 故障后的熔断冷却时间（秒）
REDIS_CONNECT_TIMEOUT: float = 1.0  # 连接超时，避免 Redis 不可用时每个请求都长时间等待
REDIS_SOCKET_TIMEOUT: float = 3.0   # 读写超时


def get_redis() -> aioredis.Redis | None:
    """获取全局 Redis 客户端；未启用、熔断中或不可用时返回 None（业务降级为直查数据库）"""
    global _redis, _redis_down_until
    if not settings.REDIS_ENABLED:
        return None
    if time.monotonic() < _redis_down_until:
        # 熔断期内直接跳过 Redis，避免每个请求都等待连接超时
        return None
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=REDIS_CONNECT_TIMEOUT,
            socket_timeout=REDIS_SOCKET_TIMEOUT,
            retry_on_timeout=False,
        )
    return _redis


async def _mark_redis_down() -> None:
    """标记 Redis 故障并进入熔断冷却，关闭旧连接"""
    global _redis, _redis_down_until
    _redis_down_until = time.monotonic() + REDIS_FAIL_COOLDOWN
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception:
            pass
        _redis = None
    logger.warning("Redis 不可用，已进入 %s 秒熔断冷却，期间直查数据库", REDIS_FAIL_COOLDOWN)


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception:
            logger.warning("关闭 Redis 连接失败", exc_info=True)
        _redis = None


# ---------- 通用缓存操作 ----------
async def cache_get(key: str) -> str | None:
    r = get_redis()
    if r is None:
        return None
    try:
        return await r.get(key)
    except Exception:
        await _mark_redis_down()
        return None


async def cache_set(key: str, value: str, ttl: int | None = None) -> None:
    r = get_redis()
    if r is None:
        return
    try:
        await r.set(key, value, ex=ttl)
    except Exception:
        await _mark_redis_down()


async def cache_delete(key: str) -> None:
    r = get_redis()
    if r is None:
        return
    try:
        await r.delete(key)
    except Exception:
        await _mark_redis_down()


async def cache_delete_pattern(pattern: str) -> None:
    """按模式批量清除缓存（SCAN + DELETE）"""
    r = get_redis()
    if r is None:
        return
    try:
        async for key in r.scan_iter(match=pattern, count=200):
            await r.delete(key)
    except Exception:
        await _mark_redis_down()


async def cache_get_json(key: str) -> Any | None:
    raw = await cache_get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


async def cache_set_json(key: str, value: Any, ttl: int | None = None) -> None:
    await cache_set(key, json.dumps(value, ensure_ascii=False, default=str), ttl=ttl)


# ---------- 缓存键构造 ----------
def get_chat_detail_key(chat_id: int) -> str:
    return f"chat:detail:{chat_id}"


def get_chat_list_key(user_id: int, page: int, size: int) -> str:
    return f"chat:list:{user_id}:{page}:{size}"


def get_history_list_key(user_id: int) -> str:
    return f"history:list:{user_id}"


def get_favorite_list_key(user_id: int, page: int, size: int) -> str:
    return f"favorite:list:{user_id}:{page}:{size}"


def get_user_token_key(user_id: int) -> str:
    return f"user:token:{user_id}"


def get_chat_context_key(chat_id: int) -> str:
    return f"chat:context:{chat_id}"


# ---------- 缓存失效（采用失效策略而非主动更新） ----------
async def invalidate_user_chat_caches(user_id: int, chat_id: int) -> None:
    """对话数据变更后清除：对话详情、上下文、对话列表、收藏列表、浏览历史缓存"""
    await cache_delete(get_chat_detail_key(chat_id))
    await cache_delete(get_chat_context_key(chat_id))
    await cache_delete_pattern(f"chat:list:{user_id}:*")
    await cache_delete_pattern(f"favorite:list:{user_id}:*")
    await cache_delete(get_history_list_key(user_id))


async def invalidate_user_favorite_caches(user_id: int) -> None:
    await cache_delete_pattern(f"favorite:list:{user_id}:*")


async def invalidate_user_history_cache(user_id: int) -> None:
    await cache_delete(get_history_list_key(user_id))