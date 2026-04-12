"""OllamaProviderV2 — Ollama'yı BaseProvider interface'ine adapte eder."""

from __future__ import annotations

import json
import os
from typing import AsyncIterator, Optional

import httpx

from .base import BaseProvider, Message, ProviderConfig, ProviderResult


class OllamaProviderV2(BaseProvider):
    """Ollama local inference — key gerektirmez, her zaman configured=True."""

    def __init__(self):
        super().__init__(ProviderConfig(
            name="ollama",
            api_key=None,  # key gereksiz
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            default_model=os.getenv("OLLAMA_MODEL", "qwen2.5:14b"),
            max_tokens=8192,
            timeout=120,
            priority=1,
        ))

    def is_configured(self) -> bool:
        return True  # Ollama her zaman yapılandırılmış sayılır

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{self.config.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> ProviderResult:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            resp = await c.post(
                f"{self.config.base_url}/api/chat",
                json={
                    "model": m,
                    "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
                    "stream": False,
                    "options": {
                        "num_ctx": max(max_tokens, 4096),
                        "temperature": temperature,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return ProviderResult(
                content=data.get("message", {}).get("content", ""),
                provider="ollama",
                model=m,
                tokens_used=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            )

    async def stream_chat(
        self, messages: list[Message], model: Optional[str] = None
    ) -> AsyncIterator[str]:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=300) as c:
            async with c.stream(
                "POST",
                f"{self.config.base_url}/api/chat",
                json={
                    "model": m,
                    "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
                    "stream": True,
                },
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{self.config.base_url}/api/tags")
                data = r.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return [self.config.default_model]
