"""Provider Router — smart task-based routing with automatic fallback."""
import os
from typing import Optional

from ultron.v2.providers.base import BaseProvider, Message, ProviderResult
from ultron.v2.providers.fallback_chain import FallbackChain

# Görev tipi → provider öncelik sırası
TASK_ROUTES = {
    "fast": ["groq", "minimax", "ollama", "cloudflare", "together"],
    "code": ["airllm", "ollama", "openrouter", "groq", "together"],
    "long": ["airllm", "gemini", "openrouter", "ollama"],
    "cheap": ["airllm", "ollama", "cloudflare", "hf", "groq"],
    "creative": ["airllm", "openrouter", "ollama", "gemini"],
    "search": ["openrouter", "gemini", "groq"],
    "self_evolve": ["airllm", "minimax", "ollama", "openrouter"],
    "deep_analysis": ["airllm", "ollama", "openrouter"],
    "sleep_mode": ["airllm"],
    "default": [
        "airllm",
        "ollama",
        "groq",
        "minimax",
        "openrouter",
        "gemini",
        "cloudflare",
        "together",
        "hf",
        "openai",
    ],
}


class ProviderRouter:
    def __init__(self):
        self.providers: dict[str, BaseProvider] = {}
        self.priority_order: list[str] = []  # Add priority order list
        self._load()

    def _load(self):
        from ultron.v2.providers.ollama_provider import OllamaProvider
        from ultron.v2.providers.groq_provider import GroqProvider
        from ultron.v2.providers.openrouter_provider import OpenRouterProvider
        from ultron.v2.providers.gemini_provider import GeminiProvider
        from ultron.v2.providers.cloudflare_provider import CloudflareProvider
        from ultron.v2.providers.together_provider import TogetherProvider
        from ultron.v2.providers.hf_provider import HFProvider
        from ultron.v2.providers.openai_provider import OpenAIProvider
        from ultron.v2.providers.minimax_provider import MiniMaxProvider
        from ultron.v2.providers.airllm_provider import AirLLMProvider

        # AirLLM Provider (highest priority - 70B/405B local)
        try:
            airllm_provider = AirLLMProvider()
            if airllm_provider.is_configured():
                self.providers["airllm"] = airllm_provider
                self.priority_order.append("airllm")
                print(f"[Router] [OK] airllm aktif ({airllm_provider.config.default_model})")
            else:
                print(f"[Router] [X] airllm yüklü değil (pip install airllm)")
        except Exception as e:
            print(f"[Router] [X] airllm yükleme hatası: {e}")

        for cls in [
            OllamaProvider,
            GroqProvider,
            MiniMaxProvider,
            OpenRouterProvider,
            GeminiProvider,
            CloudflareProvider,
            TogetherProvider,
            HFProvider,
            OpenAIProvider,
        ]:
            p = cls()
            if p.is_configured():
                self.providers[p.config.name] = p
                self.priority_order.append(p.config.name)
                print(f"[Router] [OK] {p.config.name} aktif")
            else:
                print(f"[Router] [X] {p.config.name} key yok, atlandı")

    async def route(
        self,
        messages: list[Message],
        task_type: str = "default",
        preferred_provider: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = False,
    ) -> ProviderResult:
        order = list(TASK_ROUTES.get(task_type, TASK_ROUTES["default"]))
        # Tercih edilen sağlayıcıyı öne al
        if preferred_provider and preferred_provider in self.providers:
            order = [preferred_provider] + [x for x in order if x != preferred_provider]

        chain = FallbackChain(self.providers, order)
        return await chain.execute(messages, model=model)

    async def provider_status(self) -> dict:
        """Hangi provider'lar aktif ve gecikmesi ne kadar?"""
        import asyncio
        import time

        result = {}
        for name, p in self.providers.items():
            start = time.time()
            try:
                avail = await asyncio.wait_for(p.is_available(), timeout=5)
            except Exception:
                avail = False
            result[name] = {
                "available": avail,
                "latency_ms": int((time.time() - start) * 1000),
                "model": p.config.default_model,
                "priority": p.config.priority,
            }
        return result

    def available_providers(self) -> list[str]:
        return [
            name
            for name, p in sorted(
                self.providers.items(), key=lambda x: x[1].config.priority
            )
        ]

    def list_providers(self) -> list[str]:
        return sorted(self.providers, key=lambda n: self.providers[n].config.priority)
