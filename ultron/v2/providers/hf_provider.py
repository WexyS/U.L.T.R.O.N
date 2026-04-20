"""Hugging Face Inference API — free tier."""
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


class HFProvider(BaseProvider):
    def __init__(self):
        config = ProviderConfig(
            name="hf",
            api_key=os.getenv("HF_API_KEY"),
            base_url="https://api-inference.huggingface.co/models",
            default_model=os.getenv("HF_DEFAULT_MODEL", "mistralai/Mistral-7B-Instruct-v0.3"),
            timeout=90,
            priority=7,
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

        # HF Inference API takes a single string input
        prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])

        retries = 2
        for attempt in range(retries + 1):
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.post(
                    f"{self.config.base_url}/{m}",
                    json={
                        "inputs": prompt,
                        "parameters": {"max_new_tokens": max_tokens},
                    },
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                # 503 = model loading, retry
                if resp.status_code == 503 and attempt < retries:
                    await __import__("asyncio").sleep(5)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break

        # Response format: [{"generated_text": "..."}]
        generated = data[0]["generated_text"]
        # Strip the input prompt from the output
        content = generated[len(prompt) :] if generated.startswith(prompt) else generated
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
        return bool(self.config.api_key)

    async def list_models(self) -> list[str]:
        return [
            "mistralai/Mistral-7B-Instruct-v0.3",
            "meta-llama/Llama-2-7b-chat-hf",
            "HuggingFaceH4/zephyr-7b-beta",
        ]
