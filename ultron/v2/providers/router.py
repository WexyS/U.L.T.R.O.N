import os
import time
import logging
from enum import Enum
from collections import deque
from typing import Optional, Dict, List

from ultron.v2.providers.base import BaseProvider, Message, ProviderResult
from ultron.v2.providers.fallback_chain import FallbackChain

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"     # Normal
    OPEN = "open"         # Down, skip et
    HALF_OPEN = "half_open"  # Test et

class ProviderCircuitBreaker:
    def __init__(self, name: str, failure_threshold=3, recovery_timeout=60):
        self.name = name
        self.failures = 0
        self.threshold = failure_threshold
        self.timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.last_failure = 0
    
    def should_skip(self) -> bool:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure > self.timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit Breaker [{self.name}]: HALF_OPEN (Testing...)")
                return False
            return True
        return False
    
    def record_success(self):
        if self.state != CircuitState.CLOSED:
            logger.info(f"Circuit Breaker [{self.name}]: CLOSED (Recovered)")
        self.failures = 0
        self.state = CircuitState.CLOSED
    
    def record_failure(self):
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= self.threshold:
            if self.state != CircuitState.OPEN:
                logger.warning(f"Circuit Breaker [{self.name}]: OPEN (Disabled for {self.timeout}s)")
            self.state = CircuitState.OPEN

class LatencyTracker:
    def __init__(self, window_size=10):
        self.latencies: Dict[str, deque] = {}
    
    def record(self, provider: str, latency_ms: float):
        if provider not in self.latencies:
            self.latencies[provider] = deque(maxlen=10)
        self.latencies[provider].append(latency_ms)
    
    def get_avg_latency(self, provider: str) -> float:
        if provider not in self.latencies or not self.latencies[provider]:
            return 9999.0
        return sum(self.latencies[provider]) / len(self.latencies[provider])

# Görev tipi → provider öncelik sırası
TASK_ROUTES = {
    "fast": ["brain", "groq", "minimax", "ollama", "cloudflare", "together"],
    "code": ["brain", "airllm", "ollama", "openrouter", "groq", "together"],
    "long": ["brain", "airllm", "gemini", "openrouter", "ollama"],
    "cheap": ["brain", "airllm", "ollama", "cloudflare", "hf", "groq"],
    "creative": ["brain", "airllm", "openrouter", "ollama", "gemini"],
    "search": ["brain", "openrouter", "gemini", "groq"],
    "self_evolve": ["brain", "airllm", "minimax", "ollama", "openrouter"],
    "deep_analysis": ["brain", "airllm", "ollama", "openrouter"],
    "sleep_mode": ["brain", "airllm"],
    "default": [
        "brain",
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
        self.priority_order: list[str] = []
        self.breakers: Dict[str, ProviderCircuitBreaker] = {}
        self.latency_tracker = LatencyTracker()
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
        from ultron.v2.providers.brain_provider import BrainProvider

        for cls in [
            BrainProvider, OllamaProvider, GroqProvider, MiniMaxProvider,
            OpenRouterProvider, GeminiProvider, CloudflareProvider,
            TogetherProvider, HFProvider, OpenAIProvider
        ]:
            try:
                p = cls()
                if p.is_configured():
                    name = p.config.name
                    self.providers[name] = p
                    self.priority_order.append(name)
                    self.breakers[name] = ProviderCircuitBreaker(name)
                    logger.info(f"[Router] [OK] {name} aktif")
            except Exception as e:
                logger.error(f"[Router] [X] {cls.__name__} hatası: {e}")

    async def route(
        self,
        messages: list[Message],
        task_type: str = "default",
        preferred_provider: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = False,
    ) -> ProviderResult:
        base_order = list(TASK_ROUTES.get(task_type, TASK_ROUTES["default"]))
        
        # 1. Filtrele: Açık (Open) devreleri atla
        healthy_order = [p for p in base_order if p in self.providers and not self.breakers[p].should_skip()]
        
        # 2. Sırala: Hıza göre (opsiyonel ama önerilen)
        # Latency'si 0 olmayanları hıza göre, diğerlerini orijinal sıraya göre koru
        order = sorted(healthy_order, key=lambda p: self.latency_tracker.get_avg_latency(p))

        # Tercih edilen sağlayıcıyı öne al (eğer sağlıklıysa)
        if preferred_provider and preferred_provider in order:
            order = [preferred_provider] + [x for x in order if x != preferred_provider]

        if not order:
            # Acil durum: Hiç sağlıklı provider kalmadıysa her şeyi dene (Fallback)
            order = base_order

        # FallbackChain üzerinden dene
        for p_name in order:
            p = self.providers.get(p_name)
            if not p: continue
            
            start_time = time.time()
            try:
                result = await p.chat(messages, model=model, stream=stream)
                latency = (time.time() - start_time) * 1000
                self.latency_tracker.record(p_name, latency)
                self.breakers[p_name].record_success()
                result.provider = p_name
                result.latency_ms = int(latency)
                return result
            except Exception as e:
                logger.warning(f"Provider {p_name} failed: {e}")
                self.breakers[p_name].record_failure()
                continue
                
        raise RuntimeError(f"No available providers for task {task_type}")

    async def provider_status(self) -> dict:
        """Hangi provider'lar aktif, gecikmesi ve devre durumu nedir?"""
        result = {}
        for name, p in self.providers.items():
            avg_latency = self.latency_tracker.get_avg_latency(name)
            breaker = self.breakers[name]
            result[name] = {
                "available": breaker.state != CircuitState.OPEN,
                "circuit_state": breaker.state.value,
                "avg_latency_ms": int(avg_latency) if avg_latency < 9999 else "N/A",
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
