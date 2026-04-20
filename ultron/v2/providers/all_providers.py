"""
Tüm ek sağlayıcılar: Groq, Gemini, Cloudflare, Together, HuggingFace, OpenRouter, OpenAI.
Her biri OpenAI-uyumlu REST API kullanır (en basit implementasyon).
"""

from __future__ import annotations

import os
import time
import json
from typing import Optional, AsyncIterator

import httpx

from .base import BaseProvider, Message, ProviderConfig, ProviderResult


class GroqProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        ak = api_key or os.getenv("GROQ_API_KEY")
        md = model or os.getenv("GROQ_DEFAULT_MODEL", "llama-3.3-70b-versatile")
        super().__init__(ProviderConfig(
            name="groq",
            api_key=ak,
            base_url="https://api.groq.com/openai/v1",
            default_model=md,
            max_tokens=8192, timeout=30, priority=2
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

    async def chat(self, messages, model=None, max_tokens=2048, temperature=0.7, stream=False) -> ProviderResult:
        m = model or self.config.default_model
        start = time.monotonic()
        self.stats.total_calls += 1
        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            try:
                r = await c.post(
                    f"{self.config.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    json={"model": m, "messages": [{"role": x.role, "content": x.content} for x in messages],
                        "max_tokens": max_tokens, "temperature": temperature}
                )
                r.raise_for_status()
                data = r.json()
                latency = (time.monotonic() - start) * 1000
                self.stats.successful_calls += 1
                self.stats.total_latency_ms += latency
                self.stats.last_active = datetime.now()
                self.stats.consecutive_failures = 0
                return ProviderResult(
                    content=data["choices"][0]["message"]["content"],
                    provider="groq", model=m,
                    tokens_used=data.get("usage", {}).get("total_tokens", 0)
                )
            except Exception as e:
                self.stats.failed_calls += 1
                self.stats.consecutive_failures += 1
                self.stats.last_error = str(e)
                raise

    async def stream_chat(self, messages, model=None) -> AsyncIterator[str]:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=120) as c:
            async with c.stream("POST", f"{self.config.base_url}/chat/completions",
                                headers={"Authorization": f"Bearer {self.config.api_key}"},
                                json={"model": m, "stream": True,
                                      "messages": [{"role": x.role, "content": x.content} for x in messages]}) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

    async def list_models(self) -> list[str]:
        return ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        ak = api_key or os.getenv("GEMINI_API_KEY")
        md = model or os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash-lite")
        super().__init__(ProviderConfig(
            name="gemini",
            api_key=ak,
            base_url="https://generativelanguage.googleapis.com/v1beta/models",
            default_model=md,
            max_tokens=8192, timeout=60, priority=3
        ))

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    async def is_available(self) -> bool:
        return self.is_configured()

    async def chat(self, messages, model=None, max_tokens=2048, temperature=0.7, stream=False) -> ProviderResult:
        m = model or self.config.default_model
        contents = []
        for msg in messages:
            role = "model" if msg.role == "assistant" else "user"
            parts = []
            if isinstance(msg.content, list):
                for item in msg.content:
                    if item.get("type") == "text":
                        parts.append({"text": item["text"]})
                    elif item.get("type") == "image_url":
                        url = item["image_url"]["url"]
                        if url.startswith("data:"):
                            import re
                            match = re.match(r"data:(image\/\w+);base64,(.+)", url)
                            if match:
                                media_type, data = match.groups()
                                parts.append({"inline_data": {"mime_type": media_type, "data": data}})
            else:
                parts.append({"text": msg.content})
            contents.append({"role": role, "parts": parts})

        from datetime import datetime
        start = time.monotonic()
        self.stats.total_calls += 1
        url = f"{self.config.base_url}/{m}:generateContent?key={self.config.api_key}"
        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            try:
                r = await c.post(url, json={
                    "contents": contents,
                    "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}
                })
                r.raise_for_status()
                data = r.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                latency = (time.monotonic() - start) * 1000
                self.stats.successful_calls += 1
                self.stats.total_latency_ms += latency
                self.stats.last_active = datetime.now()
                self.stats.consecutive_failures = 0
                return ProviderResult(content=content, provider="gemini", model=m)
            except Exception as e:
                self.stats.failed_calls += 1
                self.stats.consecutive_failures += 1
                self.stats.last_error = str(e)
                raise

    async def stream_chat(self, messages, model=None) -> AsyncIterator[str]:
        yield (await self.chat(messages, model)).content

    async def list_models(self) -> list[str]:
        return ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-1.5-pro"]


class CloudflareProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        ak = api_key or os.getenv("CLOUDFLARE_API_KEY")
        md = model or os.getenv("CLOUDFLARE_DEFAULT_MODEL", "@cf/meta/llama-3.1-8b-instruct")
        super().__init__(ProviderConfig(
            name="cloudflare",
            api_key=ak,
            base_url=f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CLOUDFLARE_ACCOUNT_ID', '')}/ai/run",
            default_model=md,
            max_tokens=4096, timeout=60, priority=4
        ))

    def is_configured(self) -> bool:
        return bool(self.config.api_key) and bool(os.getenv("CLOUDFLARE_ACCOUNT_ID"))

    async def is_available(self) -> bool:
        return self.is_configured()

    async def chat(self, messages, model=None, max_tokens=2048, temperature=0.7, stream=False) -> ProviderResult:
        m = model or self.config.default_model
        start = time.monotonic()
        self.stats.total_calls += 1
        url = f"{self.config.base_url}/{m}"
        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            try:
                r = await c.post(url,
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    json={"messages": [{"role": x.role, "content": x.content} for x in messages], "max_tokens": max_tokens, "temperature": temperature}
                )
                r.raise_for_status()
                data = r.json()
                content = data.get("result", {}).get("response", "")
                latency = (time.monotonic() - start) * 1000
                self.stats.successful_calls += 1
                self.stats.total_latency_ms += latency
                self.stats.last_active = datetime.now()
                self.stats.consecutive_failures = 0
                return ProviderResult(content=content, provider="cloudflare", model=m)
            except Exception as e:
                self.stats.failed_calls += 1
                self.stats.consecutive_failures += 1
                self.stats.last_error = str(e)
                raise

    async def stream_chat(self, messages, model=None) -> AsyncIterator[str]:
        yield (await self.chat(messages, model)).content

    async def list_models(self) -> list[str]:
        return ["@cf/meta/llama-3.1-8b-instruct", "@cf/meta/llama-3-8b-instruct", "@cf/mistral/mistral-7b-instruct-v0.1"]


class TogetherProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        ak = api_key or os.getenv("TOGETHER_API_KEY")
        md = model or os.getenv("TOGETHER_DEFAULT_MODEL", "meta-llama/Llama-3-8b-chat-hf")
        super().__init__(ProviderConfig(
            name="together",
            api_key=ak,
            base_url="https://api.together.xyz/v1",
            default_model=md,
            max_tokens=4096, timeout=60, priority=5
        ))

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    async def is_available(self) -> bool:
        return self.is_configured()

    async def chat(self, messages, model=None, max_tokens=2048, temperature=0.7, stream=False) -> ProviderResult:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            r = await c.post(
                f"{self.config.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={"model": m, "messages": [{"role": x.role, "content": x.content} for x in messages],
                      "max_tokens": max_tokens, "temperature": temperature}
            )
            r.raise_for_status()
            data = r.json()
            return ProviderResult(
                content=data["choices"][0]["message"]["content"],
                provider="together", model=m,
                tokens_used=data.get("usage", {}).get("total_tokens", 0)
            )

    async def stream_chat(self, messages, model=None) -> AsyncIterator[str]:
        yield (await self.chat(messages, model)).content

    async def list_models(self) -> list[str]:
        return ["meta-llama/Llama-3-8b-chat-hf", "meta-llama/Llama-3-70b-chat-hf", "mistralai/Mixtral-8x7B-Instruct-v0.1"]


class HFProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        ak = api_key or os.getenv("HF_API_KEY")
        md = model or os.getenv("HF_DEFAULT_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
        super().__init__(ProviderConfig(
            name="huggingface",
            api_key=ak,
            base_url="https://api-inference.huggingface.co/models",
            default_model=md,
            max_tokens=2048, timeout=60, priority=6
        ))

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    async def is_available(self) -> bool:
        return self.is_configured()

    async def chat(self, messages, model=None, max_tokens=2048, temperature=0.7, stream=False) -> ProviderResult:
        m = model or self.config.default_model
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            r = await c.post(
                f"{self.config.base_url}/{m}",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={"inputs": prompt, "parameters": {"max_new_tokens": max_tokens, "temperature": temperature}}
            )
            r.raise_for_status()
            data = r.json()
            content = data[0].get("generated_text", "") if data else ""
            return ProviderResult(content=content, provider="huggingface", model=m)

    async def stream_chat(self, messages, model=None) -> AsyncIterator[str]:
        yield (await self.chat(messages, model)).content

    async def list_models(self) -> list[str]:
        return ["mistralai/Mistral-7B-Instruct-v0.3", "HuggingFaceH4/zephyr-7b-beta"]


# Alias for llm_router compatibility
HuggingFaceProvider = HFProvider


class OpenRouterProvider(BaseProvider):
    """OpenRouter — tek key ile 200+ model. OpenAI-uyumlu endpoint."""

    def __init__(self):
        super().__init__(ProviderConfig(
            name="openrouter",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            default_model=os.getenv("OPENROUTER_DEFAULT_MODEL", "anthropic/claude-3-haiku"),
            max_tokens=4096, timeout=60, priority=3
        ))

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    async def is_available(self) -> bool:
        return self.is_configured()

    async def chat(self, messages, model=None, max_tokens=2048, temperature=0.7, stream=False) -> ProviderResult:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            r = await c.post(
                f"{self.config.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "Ultron v2.0",
                },
                json={
                    "model": m,
                    "messages": [{"role": x.role, "content": x.content} for x in messages],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            )
            r.raise_for_status()
            data = r.json()
            return ProviderResult(
                content=data["choices"][0]["message"]["content"],
                provider="openrouter", model=m,
                tokens_used=data.get("usage", {}).get("total_tokens", 0)
            )

    async def stream_chat(self, messages, model=None) -> AsyncIterator[str]:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=120) as c:
            async with c.stream("POST", f"{self.config.base_url}/chat/completions",
                                headers={
                                    "Authorization": f"Bearer {self.config.api_key}",
                                    "HTTP-Referer": "http://localhost:8000",
                                },
                                json={"model": m, "stream": True,
                                      "messages": [{"role": x.role, "content": x.content} for x in messages]}) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

    async def list_models(self) -> list[str]:
        return [
            "anthropic/claude-3-haiku",
            "meta-llama/llama-3.1-8b-instruct:free",
            "google/gemini-2.0-flash-lite",
            "mistralai/mistral-7b-instruct",
        ]


class OpenAIProvider(BaseProvider):
    """OpenAI — ücretli, son çare fallback. openai paketi yerine httpx ile."""

    def __init__(self):
        super().__init__(ProviderConfig(
            name="openai",
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url="https://api.openai.com/v1",
            default_model=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini"),
            max_tokens=4096, timeout=60, priority=8
        ))

    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    async def is_available(self) -> bool:
        return self.is_configured()

    async def chat(self, messages, model=None, max_tokens=2048, temperature=0.7, stream=False) -> ProviderResult:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=self.config.timeout) as c:
            r = await c.post(
                f"{self.config.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={
                    "model": m,
                    "messages": [{"role": x.role, "content": x.content} for x in messages],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            )
            r.raise_for_status()
            data = r.json()
            return ProviderResult(
                content=data["choices"][0]["message"]["content"],
                provider="openai", model=m,
                tokens_used=data.get("usage", {}).get("total_tokens", 0)
            )

    async def stream_chat(self, messages, model=None) -> AsyncIterator[str]:
        m = model or self.config.default_model
        async with httpx.AsyncClient(timeout=120) as c:
            async with c.stream("POST", f"{self.config.base_url}/chat/completions",
                                headers={"Authorization": f"Bearer {self.config.api_key}"},
                                json={"model": m, "stream": True,
                                      "messages": [{"role": x.role, "content": x.content} for x in messages]}) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

    async def list_models(self) -> list[str]:
        return ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
