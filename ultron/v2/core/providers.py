"""Extended LLM Providers for Ultron v2.0.

Includes: Groq, Google Gemini, Cloudflare Workers AI, Hugging Face, Together AI.
All providers inherit from LLMProvider base class.
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Base Types (re-exported from llm_router to avoid circular imports)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    finish_reason: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None

@dataclass
class ProviderStats:
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    last_error: Optional[str] = None
    last_active: Optional[datetime] = None
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls

    @property
    def avg_latency_ms(self) -> float:
        if self.successful_calls == 0:
            return 0.0
        return self.total_latency_ms / self.successful_calls

    @property
    def health_score(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return 0.7 * self.success_rate + 0.3 * (1.0 if self.last_active and (datetime.now() - self.last_active).total_seconds() < 300 else 0.0)

class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages, temperature=None, max_tokens=None, tools=None, stream=False) -> LLMResponse: ...
    @abstractmethod
    async def stream_chat(self, messages, temperature=None, max_tokens=None, tools=None) -> AsyncIterator[str]: ...
    @abstractmethod
    def is_available(self) -> bool: ...
    @abstractmethod
    def get_model_name(self) -> str: ...
    @property
    @abstractmethod
    def name(self) -> str: ...

# ═══════════════════════════════════════════════════════════════════════════
# 1. GROQ PROVIDER — Fastest free tier (300-500 tok/s)
# ═══════════════════════════════════════════════════════════════════════════

class GroqProvider(LLMProvider):
    """Groq — ultra-fast inference with generous free tier.
    Free models: llama-3.1-8b-instant, gemma-7b-it, mixtral-8x7b-32768
    Limits: ~30 req/min, ~10K req/day
    """
    MODELS = {
        "fast": "llama-3.1-8b-instant",
        "smart": "mixtral-8x7b-32768",
        "default": "llama-3.1-8b-instant",
    }

    def __init__(self, api_key: str = "", model: str = "fast"):
        self._api_key = api_key
        self._model_key = model
        self._base_url = "https://api.groq.com/openai/v1"
        self.stats = ProviderStats()

    @property
    def name(self): return "groq"
    def get_model_name(self): return self.MODELS.get(self._model_key, self.MODELS["default"])
    def is_available(self): return bool(self._api_key) and self._api_key.startswith("gsk_")

    async def chat(self, messages, temperature=None, max_tokens=None, tools=None, stream=False):
        if not self.is_available():
            raise RuntimeError("Groq API key not configured")
        from openai import AsyncOpenAI
        start = time.monotonic()
        self.stats.total_calls += 1
        try:
            client = AsyncOpenAI(base_url=self._base_url, api_key=self._api_key, timeout=120.0)
            model = self.get_model_name()
            kw = {"model": model, "messages": messages}
            if temperature is not None: kw["temperature"] = temperature
            if max_tokens is not None: kw["max_tokens"] = max_tokens
            if tools: kw["tools"] = tools
            resp = await client.chat.completions.create(**kw)
            await client.close()  # Prevent resource leak
            latency = (time.monotonic() - start) * 1000
            content = resp.choices[0].message.content or ""
            self.stats.successful_calls += 1
            self.stats.total_latency_ms += latency
            self.stats.last_active = datetime.now()
            self.stats.consecutive_failures = 0
            u = resp.usage
            return LLMResponse(content=content, provider=self.name, model=model,
                               tokens_used=getattr(u, "total_tokens", 0),
                               latency_ms=latency, cost_usd=0.0,  # FREE
                               finish_reason=resp.choices[0].finish_reason)
        except Exception as e:
            self.stats.failed_calls += 1
            self.stats.last_error = str(e)
            self.stats.consecutive_failures += 1
            raise

    async def stream_chat(self, messages, temperature=None, max_tokens=None, tools=None):
        from openai import AsyncOpenAI
        client = AsyncOpenAI(base_url=self._base_url, api_key=self._api_key, timeout=120.0)
        try:
            stream = await client.chat.completions.create(
                model=self.get_model_name(), messages=messages,
                temperature=temperature or 0.3, max_tokens=max_tokens or 1024, stream=True)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        finally:
            await client.close()

# ═══════════════════════════════════════════════════════════════════════════
# 2. GOOGLE GEMINI PROVIDER — Free tier, 1M+ context
# ═══════════════════════════════════════════════════════════════════════════

class GeminiProvider(LLMProvider):
    """Google Gemini — free tier via Google AI Studio.
    Free: 60 req/min, 1M tokens/day. Models: gemini-2.0-flash, gemini-2.5-flash
    """
    def __init__(self, api_key: str = "", model: str = "gemini-2.5-flash"):
        self._api_key = api_key
        self._model = model
        self.stats = ProviderStats()

    @property
    def name(self): return "gemini"
    def get_model_name(self): return self._model
    def is_available(self): return bool(self._api_key) and self._api_key.startswith("AIza")

    async def chat(self, messages, temperature=None, max_tokens=None, tools=None, stream=False):
        if not self.is_available():
            raise RuntimeError("Gemini API key not configured")
        import httpx
        start = time.monotonic()
        self.stats.total_calls += 1
        try:
            # Convert messages to Gemini format
            contents = []
            system_prompt = ""
            for msg in messages:
                role = msg.get("role", "user")
                if role == "system":
                    system_prompt = msg.get("content", "")
                elif role == "user":
                    contents.append({"role": "user", "parts": [{"text": msg.get("content", "")}]})
                elif role == "assistant":
                    contents.append({"role": "model", "parts": [{"text": msg.get("content", "")}]})

            # Add system prompt as first part of first user message
            if system_prompt and contents:
                first_parts = contents[0].get("parts", [])
                if first_parts:
                    first_parts[0]["text"] = f"{system_prompt}\n\n{first_parts[0]['text']}"

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"
            body = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature or 0.3,
                    "maxOutputTokens": max_tokens or 4096,
                }
            }
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, json=body)
                resp.raise_for_status()
                data = resp.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]

            latency = (time.monotonic() - start) * 1000
            self.stats.successful_calls += 1
            self.stats.total_latency_ms += latency
            self.stats.last_active = datetime.now()
            self.stats.consecutive_failures = 0
            return LLMResponse(content=content, provider=self.name, model=self._model,
                               latency_ms=latency, cost_usd=0.0,  # FREE tier
                               finish_reason="stop")
        except Exception as e:
            self.stats.failed_calls += 1
            self.stats.last_error = str(e)
            self.stats.consecutive_failures += 1
            raise

    async def stream_chat(self, messages, temperature=None, max_tokens=None, tools=None):
        # Streaming not implemented for Gemini free tier
        resp = await self.chat(messages, temperature, max_tokens, tools)
        yield resp.content

# ═══════════════════════════════════════════════════════════════════════════
# 3. CLOUDFLARE WORKERS AI — Free, 10K/day
# ═══════════════════════════════════════════════════════════════════════════

class CloudflareProvider(LLMProvider):
    """Cloudflare Workers AI -- free tier, 10K requests/day.
    Models: @cf/meta/llama-3.1-8b-instruct, @cf/qwen/qwen1.5-14b-chat-awq
    """
    MODELS = {
        "tiny": "@cf/meta/llama-3.1-8b-instruct",
        "small": "@cf/meta/llama-3.1-8b-instruct",
        "default": "@cf/meta/llama-3.1-8b-instruct",
    }

    def __init__(self, api_key: str = "", account_id: str = "", model: str = "small"):
        self._api_key = api_key
        self._account_id = account_id
        self._model_key = model
        self.stats = ProviderStats()

    @property
    def name(self): return "cloudflare"
    def get_model_name(self): return self.MODELS.get(self._model_key, self.MODELS["default"])
    def is_available(self): return bool(self._api_key) and bool(self._account_id)

    async def chat(self, messages, temperature=None, max_tokens=None, tools=None, stream=False):
        if not self.is_available():
            raise RuntimeError("Cloudflare credentials not configured")
        import httpx
        start = time.monotonic()
        self.stats.total_calls += 1
        try:
            model = self.get_model_name()
            url = f"https://api.cloudflare.com/client/v4/accounts/{self._account_id}/ai/run/{model}"
            body = {
                "messages": messages,
                "temperature": temperature or 0.3,
                "max_tokens": max_tokens or 1024,
            }
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, json=body, headers={
                    "Authorization": f"Bearer {self._api_key}",
                })
                resp.raise_for_status()
                data = resp.json()
                content = data.get("result", {}).get("response", "")

            latency = (time.monotonic() - start) * 1000
            self.stats.successful_calls += 1
            self.stats.total_latency_ms += latency
            self.stats.last_active = datetime.now()
            self.stats.consecutive_failures = 0
            return LLMResponse(content=content, provider=self.name, model=model,
                               latency_ms=latency, cost_usd=0.0,  # FREE tier
                               finish_reason="stop")
        except Exception as e:
            self.stats.failed_calls += 1
            self.stats.last_error = str(e)
            self.stats.consecutive_failures += 1
            raise

    async def stream_chat(self, messages, temperature=None, max_tokens=None, tools=None):
        resp = await self.chat(messages, temperature, max_tokens, tools)
        yield resp.content

# ═══════════════════════════════════════════════════════════════════════════
# 4. TOGETHER AI PROVIDER — $25 free credits
# ═══════════════════════════════════════════════════════════════════════════

class TogetherProvider(LLMProvider):
    """Together AI — $25 free credits on signup.
    Models: Qwen 2.5 72B, Llama 3.1 405B, Mixtral, etc.
    """
    def __init__(self, api_key: str = "", model: str = "Qwen/Qwen2.5-72B-Instruct-Turbo"):
        self._api_key = api_key
        self._model = model
        self.stats = ProviderStats()

    @property
    def name(self): return "together"
    def get_model_name(self): return self._model
    def is_available(self): return bool(self._api_key)

    async def chat(self, messages, temperature=None, max_tokens=None, tools=None, stream=False):
        if not self.is_available():
            raise RuntimeError("Together AI key not configured")
        from openai import AsyncOpenAI
        start = time.monotonic()
        self.stats.total_calls += 1
        try:
            client = AsyncOpenAI(base_url="https://api.together.xyz/v1", api_key=self._api_key, timeout=120.0)
            kw = {"model": self._model, "messages": messages}
            if temperature is not None: kw["temperature"] = temperature
            if max_tokens is not None: kw["max_tokens"] = max_tokens
            if tools: kw["tools"] = tools
            resp = await client.chat.completions.create(**kw)
            await client.close()  # Prevent resource leak
            latency = (time.monotonic() - start) * 1000
            content = resp.choices[0].message.content or ""
            self.stats.successful_calls += 1
            self.stats.total_latency_ms += latency
            self.stats.last_active = datetime.now()
            self.stats.consecutive_failures = 0
            return LLMResponse(content=content, provider=self.name, model=self._model,
                               tokens_used=getattr(resp.usage, "total_tokens", 0),
                               latency_ms=latency, cost_usd=0.0,
                               finish_reason=resp.choices[0].finish_reason)
        except Exception as e:
            self.stats.failed_calls += 1
            self.stats.last_error = str(e)
            self.stats.consecutive_failures += 1
            raise

    async def stream_chat(self, messages, temperature=None, max_tokens=None, tools=None):
        from openai import AsyncOpenAI
        client = AsyncOpenAI(base_url="https://api.together.xyz/v1", api_key=self._api_key, timeout=120.0)
        try:
            stream = await client.chat.completions.create(
                model=self._model, messages=messages,
                temperature=temperature or 0.3, max_tokens=max_tokens or 1024, stream=True)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        finally:
            await client.close()

# ═══════════════════════════════════════════════════════════════════════════
# 5. HUGGING FACE PROVIDER — Free Inference API
# ═══════════════════════════════════════════════════════════════════════════

class HuggingFaceProvider(LLMProvider):
    """Hugging Face Inference API — free tier.
    Models: Any HF model with inference API enabled.
    """
    DEFAULT_MODEL = "Qwen/Qwen2.5-72B-Instruct"

    def __init__(self, api_key: str = "", model: str = None):
        self._api_key = api_key
        self._model = model or self.DEFAULT_MODEL
        self.stats = ProviderStats()

    @property
    def name(self): return "huggingface"
    def get_model_name(self): return self._model
    def is_available(self): return bool(self._api_key)

    async def chat(self, messages, temperature=None, max_tokens=None, tools=None, stream=False):
        if not self.is_available():
            raise RuntimeError("Hugging Face token not configured")
        import httpx
        start = time.monotonic()
        self.stats.total_calls += 1
        try:
            # HF Inference API format
            payload = {
                "inputs": "\n".join(m.get("content", "") for m in messages),
                "parameters": {
                    "temperature": temperature or 0.3,
                    "max_new_tokens": max_tokens or 1024,
                    "return_full_text": False,
                }
            }
            url = f"https://api-inference.huggingface.co/models/{self._model}"
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, json=payload, headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                })
                resp.raise_for_status()
                data = resp.json()
                content = data[0].get("generated_text", "") if isinstance(data, list) else data.get("generated_text", "")

            latency = (time.monotonic() - start) * 1000
            self.stats.successful_calls += 1
            self.stats.total_latency_ms += latency
            self.stats.last_active = datetime.now()
            self.stats.consecutive_failures = 0
            return LLMResponse(content=content.strip(), provider=self.name, model=self._model,
                               latency_ms=latency, cost_usd=0.0,  # FREE
                               finish_reason="stop")
        except Exception as e:
            self.stats.failed_calls += 1
            self.stats.last_error = str(e)
            self.stats.consecutive_failures += 1
            raise

    async def stream_chat(self, messages, temperature=None, max_tokens=None, tools=None):
        resp = await self.chat(messages, temperature, max_tokens, tools)
        yield resp.content
