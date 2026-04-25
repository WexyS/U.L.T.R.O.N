"""Google Gemini Provider — 1M context, 60 req/min free."""
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


class GeminiProvider(BaseProvider):
    def __init__(self):
        config = ProviderConfig(
            name="gemini",
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta",
            default_model=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash-lite"),
            timeout=60,
            priority=4,
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

        # Extract system message
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                role = "user" if msg.role == "user" else "model"
                chat_messages.append(
                    {"role": role, "parts": [{"text": msg.content}]}
                )

        body = {
            "contents": chat_messages,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_msg:
            body["systemInstruction"] = {"parts": [{"text": system_msg}]}

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            resp = await client.post(
                f"{self.config.base_url}/models/{m}:generateContent",
                params={"key": self.config.api_key},
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return ProviderResult(
            content=content,
            provider=self.config.name,
            model=m,
            tokens_used=0,  # Gemini doesn't return token count in this API
            latency_ms=int((time.time() - start) * 1000),
        )

    async def stream_chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        # Gemini streaming via REST — simplified
        result = await self.chat(messages, model=model)
        yield result.content

    async def is_available(self) -> bool:
        return bool(self.config.api_key)

    async def list_models(self) -> list[str]:
        return [
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]
