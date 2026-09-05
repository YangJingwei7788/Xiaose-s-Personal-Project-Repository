"""统一大模型调用客户端

支持三种来源：
- public   ：服务端配置的公共 Ollama（默认）
- local    ：用户自己的本地 Ollama 兼容服务（输入地址即可）
- deepseek ：DeepSeek 官方 API（OpenAI 兼容接口，需 API Key）
"""
import json
import logging
from typing import AsyncIterator

import httpx

from xiaosemiao_ai.config.settings import settings

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-flash"


async def _stream_ollama(messages: list[dict], base_url: str, model: str, timeout: float) -> AsyncIterator[str]:
    """Ollama /api/chat NDJSON 流式"""
    payload = {"model": model, "messages": messages, "stream": True}
    url = f"{base_url.rstrip('/')}/api/chat"
    async with httpx.AsyncClient(timeout=timeout) as client:
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


async def _stream_openai(messages: list[dict], base_url: str, api_key: str, model: str, timeout: float) -> AsyncIterator[str]:
    """OpenAI 兼容接口（DeepSeek）SSE 流式"""
    payload = {"model": model, "messages": messages, "stream": True}
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                choices = data.get("choices") or []
                if not choices:
                    continue
                delta = (choices[0].get("delta") or {}).get("content")
                if delta:
                    yield delta


async def stream_chat(
    messages: list[dict],
    *,
    provider: str = "public",
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    timeout: float | None = None,
) -> AsyncIterator[str]:
    """统一入口：根据 provider 路由到对应大模型"""
    timeout = timeout or settings.OLLAMA_TIMEOUT
    if provider == "deepseek":
        base = base_url or DEEPSEEK_BASE_URL
        mdl = model or DEEPSEEK_DEFAULT_MODEL
        if not api_key:
            raise ValueError("DeepSeek 需要 API Key")
        async for delta in _stream_openai(messages, base, api_key, mdl, timeout):
            yield delta
        return
    # public / local 均走 Ollama 兼容协议
    base = base_url or settings.OLLAMA_BASE_URL
    mdl = model or settings.OLLAMA_MODEL
    async for delta in _stream_ollama(messages, base, mdl, timeout):
        yield delta
