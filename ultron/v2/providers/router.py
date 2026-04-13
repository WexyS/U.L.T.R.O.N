"""Provider Router — smart task-based routing with automatic fallback."""
import os
from typing import Optional

from ultron.v2.providers.base import BaseProvider, Message, ProviderResult
from ultron.v2.providers.fallback_chain import FallbackChain

# Görev tipi → provider öncelik sırası
TASK_ROUTES = {
    "fast": ["groq", "ollama", "cloudflare", "together"],
    "code": ["ollama", "openrouter", "groq", "together"],
    "long": ["gemini", "openrouter", "ollama"],
    "cheap": ["ollama", "cloudflare", "hf", "groq"],
    "creative": ["openrouter", "ollama", "gemini"],
    "search": ["openrouter", "gemini", "groq"],
    "deep_analysis": ["airllm_405b", "ollama", "openrouter"],  # YENİ: 405B için
    "sleep_mode": ["airllm_405b"],  # YENİ: Uyku modu
    "default": [
        "ollama",
        "groq",
        "openrouter",
        "gemini",
        "cloudflare",
        "together",
        "hf",
        "openai",
        "airllm_405b",  # YENİ: 405B fallback olarak
    ],
}


class ProviderRouter:
    def __init__(self):
        self.providers: dict[str, BaseProvider] = {}
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
        from ultron.v2.providers.airllm_provider import create_provider as create_airllm

        for cls in [
            OllamaProvider,
            GroqProvider,
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
                print(f"[Router] ✓ {p.config.name} aktif")
            else:
                print(f"[Router] ✗ {p.config.name} key yok, atlandı")
        
        # AirLLM Provider (405B - 4-bit compression)
        try:
            import airllm
            airllm_config = {
                "model_name": os.environ.get("AIRLLM_MODEL", "meta-llama/Llama-3.1-405B"),
                "compression": os.environ.get("AIRLLM_COMPRESSION", "4bit"),
                "prefetching": os.environ.get("AIRLLM_PREFETCHING", "true").lower() == "true"
            }
            airllm_provider = create_airllm(airllm_config)
            self.providers["airllm_405b"] = airllm_provider
            print(f"[Router] ✓ airllm_405b aktif (405B 4-bit, ~230GB disk, ~8GB VRAM)")
        except ImportError:
            print(f"[Router] ✗ airllm_405b yüklü değil (pip install airllm)")
        except Exception as e:
            print(f"[Router] ✗ airllm_405b yükleme hatası: {e}")

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
