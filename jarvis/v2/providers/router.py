"""ProviderRouter — Göreve göre akıllı yönlendirme + fallback zinciri."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Optional

import structlog

from .base import BaseProvider, Message, ProviderResult
from .fallback_chain import FallbackChain

logger = structlog.get_logger()


class ProviderRouter:
    """Görev tipine göre en uygun sağlayıcıyı seçer."""

    TASK_PRIORITY = {
        "fast": ["groq", "deepseek", "fireworks", "ollama", "cloudflare", "openrouter"],
        "code": ["ollama", "deepseek", "anthropic", "openrouter", "groq", "together"],
        "long": ["gemini", "openrouter", "anthropic", "ollama"],
        "cheap": ["ollama", "deepseek", "cloudflare", "huggingface", "groq"],
        "creative": ["anthropic", "openrouter", "mistral", "ollama", "gemini"],
        "private": ["ollama", "mistral", "cohere"],
        "default": [
            "ollama",
            "groq",
            "deepseek",
            "anthropic",
            "openrouter",
            "gemini",
            "mistral",
            "fireworks",
            "cloudflare",
            "together",
            "cohere",
            "huggingface",
            "openai",
        ],
    }

    def __init__(self):
        self.providers: dict[str, BaseProvider] = {}
        self._load_providers()

    def _load_providers(self):
        """Sadece .env'de key'i olan sağlayıcıları yükle."""
        from .all_providers import (
            CloudflareProvider,
            GeminiProvider,
            GroqProvider,
            HFProvider,
            OpenAIProvider,
            OpenRouterProvider,
            TogetherProvider,
        )
        from .extra_providers import (
            AnthropicProvider,
            CohereProvider,
            DeepSeekProvider,
            FireworksProvider,
            MistralProvider,
        )

        candidates: list[BaseProvider] = [
            self._make_ollama_provider(),
            GroqProvider(),
            DeepSeekProvider(),      # ucuz + güçlü — öncelikli
            OpenRouterProvider(),
            AnthropicProvider(),
            GeminiProvider(),
            MistralProvider(),
            FireworksProvider(),
            CloudflareProvider(),
            TogetherProvider(),
            CohereProvider(),
            HFProvider(),
            OpenAIProvider(),
        ]
        for p in candidates:
            if p.is_configured():
                self.providers[p.config.name] = p

    @staticmethod
    def _make_ollama_provider():
        """Ollama — yerel, key gerektirmez, her zaman dene.
        BaseProvider interface'ine adapter."""
        from .ollama_adapter import OllamaProviderV2
        return OllamaProviderV2()

    async def route(
        self,
        messages: list[Message],
        task_type: str = "default",
        preferred_provider: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = False,
    ) -> ProviderResult:
        order = list(self.TASK_PRIORITY.get(task_type, self.TASK_PRIORITY["default"]))

        if preferred_provider and preferred_provider in self.providers:
            order = [preferred_provider] + [
                p for p in order if p != preferred_provider
            ]

        chain = FallbackChain(self.providers, order)
        return await chain.execute(messages, model=model, stream=stream)

    def available_providers(self) -> list[str]:
        return list(self.providers.keys())

    async def provider_status(self) -> dict:
        """Her sağlayıcının erişilebilirlik durumunu döndür."""
        results = {}
        for name, provider in self.providers.items():
            start = time.time()
            try:
                available = await asyncio.wait_for(
                    provider.is_available(), timeout=5
                )
                latency_ms = int((time.time() - start) * 1000)
                results[name] = {
                    "available": available,
                    "latency_ms": latency_ms,
                    "configured": provider.is_configured(),
                    "model": provider.config.default_model,
                }
            except Exception:
                results[name] = {
                    "available": False,
                    "latency_ms": -1,
                    "configured": provider.is_configured(),
                    "model": provider.config.default_model,
                }
        return results
