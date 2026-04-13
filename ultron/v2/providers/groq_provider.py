"""Groq Provider — ultra-fast inference, free tier."""
import os
import time
from typing import AsyncIterator, Optional

import httpx

from ultron.v2.providers.base import (
    BaseProvider,
    Message,
    ProviderConfig,
    ProviderResult,
)


class GroqProvider(BaseProvider):
    def __init__(self):
        config = ProviderConfig(
            name="groq",
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
            default_model=os.getenv("GROQ_DEFAULT_MODEL", "llama-3.3-70b-versatile"),
            timeout=30,
            priority=2,
        )
        super().__init__(config)

    async def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> ProviderResult:
        model_name = model or self.config.default_model
        start = time.time()

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            resp = await client.post(
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": model_name,
                    "messages": [msg.model_dump() for msg in messages],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        content = choice["message"]["content"]
        usage = data.get("usage", {})
        return ProviderResult(
            content=content,
            provider=self.config.name,
            model=m,
            tokens_used=usage.get("total_tokens", 0),
            latency_ms=int((time.time() - start) * 1000),
        )

    async def stream_chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        model_name = model or self.config.default_model
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": model_name,
                    "messages": [msg.model_dump() for msg in messages],
                    "stream": True,
                },
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

    async def is_available(self) -> bool:
        return bool(self.config.api_key)

    def get_model_name(self) -> str:
        """Aktif model adını döndür"""
        return self.config.default_model

    async def list_models(self) -> list[str]:
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]
