"""Ollama Provider — local, free, no API key required."""
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


class OllamaProvider(BaseProvider):
    def __init__(self):
        config = ProviderConfig(
            name="ollama",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            default_model=os.getenv("OLLAMA_MODEL", "qwen2.5:14b"),
            timeout=120,
            priority=1,
        )
        super().__init__(config)

    def is_configured(self) -> bool:
        return True  # Ollama never needs an API key

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
                f"{self.config.base_url}/api/chat",
                json={
                    "model": model_name,
                    "messages": [msg.model_dump() for msg in messages],
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data.get("message", {}).get("content", "")
        return ProviderResult(
            content=content,
            provider=self.config.name,
            model=model_name,
            tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
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
                f"{self.config.base_url}/api/chat",
                json={
                    "model": model_name,
                    "messages": [msg.model_dump() for msg in messages],
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        import json
                        chunk = json.loads(line)
                        if chunk.get("done"):
                            break
                        yield chunk.get("message", {}).get("content", "")

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.config.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.config.base_url}/api/tags")
                resp.raise_for_status()
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []
