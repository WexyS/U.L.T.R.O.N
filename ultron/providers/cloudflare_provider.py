"""Cloudflare Workers AI Provider — free, 10K/day."""
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


class CloudflareProvider(BaseProvider):
    def __init__(self):
        config = ProviderConfig(
            name="cloudflare",
            api_key=os.getenv("CLOUDFLARE_API_KEY"),
            base_url=f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CLOUDFLARE_ACCOUNT_ID', '')}/ai/run",
            default_model=os.getenv("CLOUDFLARE_DEFAULT_MODEL", "@cf/meta/llama-3.1-8b-instruct"),
            timeout=45,
            priority=5,
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
                f"{self.config.base_url}/{m}",
                json={
                    "messages": [m.model_dump() for m in messages],
                    "max_tokens": max_tokens,
                },
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

        content = data.get("result", {}).get("response", "")
        return ProviderResult(
            content=content,
            provider=self.config.name,
            model=m,
            tokens_used=0,
            latency_ms=int((time.time() - start) * 1000),
        )

    async def stream_chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        result = await self.chat(messages, model=model)
        yield result.content

    async def is_available(self) -> bool:
        return bool(self.config.api_key) and bool(os.getenv("CLOUDFLARE_ACCOUNT_ID"))

    async def list_models(self) -> list[str]:
        return [
            "@cf/meta/llama-3.1-8b-instruct",
            "@cf/meta/llama-3-8b-instruct",
            "@cf/mistral/mistral-7b-instruct-v0.1",
            "@cf/qwen/qwen1.5-14b-chat",
        ]
