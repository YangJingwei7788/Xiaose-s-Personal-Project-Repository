"""Ollama 本地大模型调用封装（流式）"""
import json
import logging
from typing import AsyncIterator

import httpx

from xiaosemiao_ai.config.settings import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """封装 Ollama /api/chat 流式接口"""

    def __init__(self, base_url: str, model: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def stream_chat(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
        """按 NDJSON 流式读取回复，逐个返回内容增量"""
        payload = {"model": model or self.model, "messages": messages, "stream": True}
        url = f"{self.base_url}/api/chat"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if data.get("done"):
                        break
                    delta = (data.get("message") or {}).get("content") or ""
                    if delta:
                        yield delta


_client = OllamaClient(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.OLLAMA_MODEL,
    timeout=settings.OLLAMA_TIMEOUT,
)


def get_ollama_client() -> OllamaClient:
    return _client


async def stream_chat(messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
    """业务侧统一入口：流式获取 AI 回复增量"""
    async for delta in get_ollama_client().stream_chat(messages, model=model):
        yield delta