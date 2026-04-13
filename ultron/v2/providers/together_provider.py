"""Together AI Provider — $25 free credit."""
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


class TogetherProvider(BaseProvider):
    def __init__(self):
        config = ProviderConfig(
            name="together",
            api_key=os.getenv("TOGETHER_API_KEY"),
            base_url="https://api.together.xyz/v1",
            default_model=os.getenv("TOGETHER_DEFAULT_MODEL", "meta-llama/Llama-3-8b-chat-hf"),
            timeout=60,
            priority=6,
        )
        super().__init__(config)

    async def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> ProviderResult:
        m = model or self.config.default_model
        start = time.time()

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            resp = await client.post(
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": m,
                    "messages": [m.model_dump() for m in messages],
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
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": m,
                    "messages": [m.model_dump() for m in messages],
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

    async def list_models(self) -> list[str]:
        return [
            "meta-llama/Llama-3-8b-chat-hf",
            "meta-llama/Llama-3-70b-chat-hf",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "google/gemma-2-9b-it",
        ]
