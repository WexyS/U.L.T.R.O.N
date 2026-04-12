"""
Ek sağlayıcılar: Anthropic, Mistral, Cohere, DeepSeek, Fireworks.
.env'de key'i olanlar otomatik yüklenir.
"""

from __future__ import annotations

import json
import os
from typing import AsyncIterator

import httpx

from .base import BaseProvider, Message, ProviderConfig, ProviderResult


# ──────────────────────────────────────────────────────────────
# Anthropic Claude
# ──────────────────────────────────────────────────────────────
class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        ak = api_key or os.getenv("ANTHROPIC_API_KEY")
        md = model or "claude-3-5-sonnet-20241022"
        super().__init__(ProviderConfig(
            name="anthropic",
            api_key=ak,
            base_url="https://api.anthropic.com/v1",
            default_model=md,
            max_tokens=8192, timeout=60, priority=2,
        ))

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    async def is_available(self) -> bool:
        return self.is_configured()

    async def chat(self, messages, model=None, max_tokens=2048,
                   temperature=0.7, stream=False) -> ProviderResult:
        m = model or self.config.default_model
        # Anthropic: system prompt ayrık, messages farklı formatta
        system_msg = ""
        chat_msgs = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                chat_msgs.append({"role": msg.role, "content": msg.content})

        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            r = await c.post(
                f"{self.config.base_url}/messages",
                headers={
                    "x-api-key": self.config.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": m,
                    "messages": chat_msgs,
                    "system": system_msg,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            r.raise_for_status()
            data = r.json()
            return ProviderResult(
                content=data["content"][0]["text"],
                provider="anthropic", model=m,
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
            )

    async def stream_chat(self, messages, model=None) -> AsyncIterator[str]:
        # Anthropic SSE streaming
        m = model or self.config.default_model
        system_msg = ""
        chat_msgs = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                chat_msgs.append({"role": msg.role, "content": msg.content})

        async with httpx.AsyncClient(timeout=120) as c:
            async with c.stream("POST", f"{self.config.base_url}/messages",
                                headers={
                                    "x-api-key": self.config.api_key,
                                    "anthropic-version": "2023-06-01",
                                    "content-type": "application/json",
                                },
                                json={
                                    "model": m, "messages": chat_msgs,
                                    "system": system_msg,
                                    "max_tokens": 4096, "stream": True,
                                }) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            chunk = json.loads(line[6:])
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta["text"]
                        except (json.JSONDecodeError, KeyError):
                            continue

    async def list_models(self) -> list[str]:
        return ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229"]


# ──────────────────────────────────────────────────────────────
# Mistral AI
# ──────────────────────────────────────────────────────────────
class MistralProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        ak = api_key or os.getenv("MISTRAL_API_KEY")
        md = model or "mistral-large-latest"
        super().__init__(ProviderConfig(
            name="mistral",
            api_key=ak,
            base_url="https://api.mistral.ai/v1",
            default_model=md,
            max_tokens=8192, timeout=60, priority=3,
        ))

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    async def is_available(self) -> bool:
        if not self.is_configured():
            return False
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{self.config.base_url}/models",
                                headers={"Authorization": f"Bearer {self.config.api_key}"})
                return r.status_code == 200
        except Exception:
            return False

    async def chat(self, messages, model=None, max_tokens=2048,
                   temperature=0.7, stream=False) -> ProviderResult:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            r = await c.post(
                f"{self.config.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={"model": m,
                      "messages": [{"role": x.role, "content": x.content} for x in messages],
                      "max_tokens": max_tokens, "temperature": temperature},
            )
            r.raise_for_status()
            data = r.json()
            return ProviderResult(
                content=data["choices"][0]["message"]["content"],
                provider="mistral", model=m,
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
            )

    async def stream_chat(self, messages, model=None) -> AsyncIterator[str]:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=120) as c:
            async with c.stream("POST", f"{self.config.base_url}/chat/completions",
                                headers={"Authorization": f"Bearer {self.config.api_key}"},
                                json={"model": m, "stream": True,
                                      "messages": [{"role": x.role, "content": x.content}
                                                    for x in messages]}) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

    async def list_models(self) -> list[str]:
        return ["mistral-large-latest", "mistral-small-latest",
                "open-mistral-nemo", "codestral-latest"]


# ──────────────────────────────────────────────────────────────
# Cohere
# ──────────────────────────────────────────────────────────────
class CohereProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        ak = api_key or os.getenv("COHERE_API_KEY")
        md = model or "command-r-plus"
        super().__init__(ProviderConfig(
            name="cohere",
            api_key=ak,
            base_url="https://api.cohere.ai/v1",
            default_model=md,
            max_tokens=4096, timeout=60, priority=4,
        ))

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    async def is_available(self) -> bool:
        return self.is_configured()

    async def chat(self, messages, model=None, max_tokens=2048,
                   temperature=0.7, stream=False) -> ProviderResult:
        m = model or self.config.default_model
        # Cohere: son mesajı "message" olarak, öncekileri chat_history olarak gönder
        last = messages[-1] if messages else Message(role="user", content="")
        history = [{"role": m.role, "message": m.content} for m in messages[:-1]]

        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            r = await c.post(
                f"{self.config.base_url}/chat",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "content-type": "application/json",
                },
                json={
                    "model": m,
                    "message": last.content,
                    "chat_history": history,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            r.raise_for_status()
            data = r.json()
            return ProviderResult(
                content=data.get("text", ""),
                provider="cohere", model=m,
                tokens_used=0,
            )

    async def stream_chat(self, messages, model=None) -> AsyncIterator[str]:
        # Cohere streaming — chat endpoint stream parametresi ile
        m = model or self.config.default_model
        last = messages[-1] if messages else Message(role="user", content="")
        history = [{"role": msg.role, "message": msg.content} for msg in messages[:-1]]

        async with httpx.AsyncClient(timeout=120) as c:
            async with c.stream("POST", f"{self.config.base_url}/chat",
                                headers={"Authorization": f"Bearer {self.config.api_key}"},
                                json={"model": m, "message": last.content,
                                      "chat_history": history,
                                      "stream": True}) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        if chunk.get("event_type") == "text-generation":
                            yield chunk.get("text", "")
                    except json.JSONDecodeError:
                        continue

    async def list_models(self) -> list[str]:
        return ["command-r-plus", "command-r", "command", "command-light"]


# ──────────────────────────────────────────────────────────────
# DeepSeek
# ──────────────────────────────────────────────────────────────
class DeepSeekProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        ak = api_key or os.getenv("DEEPSEEK_API_KEY")
        md = model or "deepseek-chat"
        super().__init__(ProviderConfig(
            name="deepseek",
            api_key=ak,
            base_url="https://api.deepseek.com/v1",
            default_model=md,
            max_tokens=8192, timeout=60, priority=2,
        ))

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    async def is_available(self) -> bool:
        if not self.is_configured():
            return False
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{self.config.base_url}/models",
                                headers={"Authorization": f"Bearer {self.config.api_key}"})
                return r.status_code == 200
        except Exception:
            return False

    async def chat(self, messages, model=None, max_tokens=2048,
                   temperature=0.7, stream=False) -> ProviderResult:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            r = await c.post(
                f"{self.config.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={"model": m,
                      "messages": [{"role": x.role, "content": x.content} for x in messages],
                      "max_tokens": max_tokens, "temperature": temperature},
            )
            r.raise_for_status()
            data = r.json()
            return ProviderResult(
                content=data["choices"][0]["message"]["content"],
                provider="deepseek", model=m,
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
            )

    async def stream_chat(self, messages, model=None) -> AsyncIterator[str]:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=120) as c:
            async with c.stream("POST", f"{self.config.base_url}/chat/completions",
                                headers={"Authorization": f"Bearer {self.config.api_key}"},
                                json={"model": m, "stream": True,
                                      "messages": [{"role": x.role, "content": x.content}
                                                    for x in messages]}) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

    async def list_models(self) -> list[str]:
        return ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]


# ──────────────────────────────────────────────────────────────
# Fireworks AI
# ──────────────────────────────────────────────────────────────
class FireworksProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        ak = api_key or os.getenv("FIREWORKS_API_KEY")
        md = model or "accounts/fireworks/models/llama-v3p1-8b-instruct"
        super().__init__(ProviderConfig(
            name="fireworks",
            api_key=ak,
            base_url="https://api.fireworks.ai/inference/v1",
            default_model=md,
            max_tokens=4096, timeout=60, priority=3,
        ))

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    async def is_available(self) -> bool:
        return self.is_configured()

    async def chat(self, messages, model=None, max_tokens=2048,
                   temperature=0.7, stream=False) -> ProviderResult:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            r = await c.post(
                f"{self.config.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={"model": m,
                      "messages": [{"role": x.role, "content": x.content} for x in messages],
                      "max_tokens": max_tokens, "temperature": temperature},
            )
            r.raise_for_status()
            data = r.json()
            return ProviderResult(
                content=data["choices"][0]["message"]["content"],
                provider="fireworks", model=m,
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
            )

    async def stream_chat(self, messages, model=None) -> AsyncIterator[str]:
        yield (await self.chat(messages, model)).content

    async def list_models(self) -> list[str]:
        return [
            "accounts/fireworks/models/llama-v3p1-8b-instruct",
            "accounts/fireworks/models/llama-v3p1-70b-instruct",
            "accounts/fireworks/models/mixtral-8x7b-instruct",
        ]
