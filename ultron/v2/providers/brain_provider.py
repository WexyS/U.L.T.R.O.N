"""Ultron Brain Provider — local fine-tuned model on port 8001."""
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


class BrainProvider(BaseProvider):
    def __init__(self):
        config = ProviderConfig(
            name="brain",
            api_key="sk-ultron",  # dummy key
            base_url="http://localhost:8001/v1",
            default_model="qwen", # Ultron Factory typically uses 'qwen' as dummy name
            timeout=120,
            priority=0, # Highest priority
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
            model=model_name,
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
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except:
                            continue

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{os.path.dirname(self.config.base_url)}/models")
                return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        return ["qwen"]
