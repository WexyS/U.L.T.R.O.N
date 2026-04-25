"""MiniMax M2.7 Provider — Self-evolving model with agentic tool use.

MiniMax M2.7:
- 10B parameters, flagship-level performance
- Self-learning and adaptive reasoning
- Excellent for agentic workflows and tool use
- Available via OpenRouter and OpenAI-compatible API
- Cost-effective (~$0.10/1M tokens)

API Endpoints:
- OpenRouter: https://openrouter.ai/api/v1
- Official: https://api.minimaxi.com/v1

Model IDs:
- minimax/minimax-m2.7
- minimax/minimax-m2.7-highspeed (faster, slightly less accurate)
"""

import os
import time
from typing import AsyncIterator, Optional

import httpx

from ultron.providers.base import (
    BaseProvider,
    Message,
    ProviderConfig,
    ProviderResult,
)


class MiniMaxProvider(BaseProvider):
    """MiniMax M2.7 Provider — Self-evolving model."""

    def __init__(self):
        config = ProviderConfig(
            name="minimax",
            api_key=os.getenv("MINIMAX_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("MINIMAX_BASE_URL", "https://openrouter.ai/api/v1"),
            default_model=os.getenv("MINIMAX_DEFAULT_MODEL", "minimax/minimax-m2.7"),
            timeout=60,
            priority=3,  # After Groq, before OpenRouter
        )
        super().__init__(config)

        # If using OpenRouter, adjust headers
        self._use_openrouter = "openrouter.ai" in config.base_url

    async def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> ProviderResult:
        m = model or self.config.default_model
        start = time.time()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        # OpenRouter specific headers
        if self._use_openrouter:
            headers["HTTP-Referer"] = "https://github.com/Ultron-Assistant"
            headers["X-Title"] = "Ultron AI Assistant"

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            resp = await client.post(
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": m,
                    "messages": [msg.model_dump() for msg in messages],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                headers=headers,
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
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        if self._use_openrouter:
            headers["HTTP-Referer"] = "https://github.com/Ultron-Assistant"
            headers["X-Title"] = "Ultron AI Assistant"

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": m,
                    "messages": [msg.model_dump() for msg in messages],
                    "stream": True,
                },
                headers=headers,
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
        """Return the active model name."""
        return self.config.default_model

    async def list_models(self) -> list[str]:
        return [
            "minimax/minimax-m2.7",
            "minimax/minimax-m2.7-highspeed",
        ]
