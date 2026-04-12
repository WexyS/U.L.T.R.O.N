"""FallbackChain — Otomatik yedekleme + geçici kara liste."""

from __future__ import annotations

import time
from typing import Optional

import structlog

from .base import BaseProvider, Message, ProviderResult

logger = structlog.get_logger()


class FallbackChain:
    def __init__(self, providers: dict[str, BaseProvider], order: list[str]):
        self.providers = providers
        self.order = order
        self._failed_providers: set[str] = set()
        self._fail_timestamps: dict[str, float] = {}
        self.RECOVERY_SECONDS = 300  # 5 dakika sonra tekrar dene

    async def execute(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        stream: bool = False,
    ) -> ProviderResult:
        import asyncio

        for name in self.order:
            if name not in self.providers:
                continue
            if self._is_blocked(name):
                logger.debug("provider_blocked", provider=name)
                continue

            provider = self.providers[name]
            try:
                if not await provider.is_available():
                    self._mark_failed(name)
                    logger.warning("provider_unavailable", provider=name)
                    continue

                start = time.time()
                result = await asyncio.wait_for(
                    provider.chat(messages, model=model),
                    timeout=provider.config.timeout,
                )
                result.latency_ms = int((time.time() - start) * 1000)
                logger.info(
                    "provider_success",
                    provider=name,
                    latency_ms=result.latency_ms,
                )
                return result

            except asyncio.TimeoutError:
                logger.warning("provider_timeout", provider=name)
                self._mark_failed(name)
            except Exception as e:
                logger.warning("provider_error", provider=name, error=str(e))
                self._mark_failed(name)

        raise RuntimeError(
            f"Tüm sağlayıcılar başarısız: {self.order}. "
            "Ollama çalışıyor mu? API keyleri doğru mu?"
        )

    def _is_blocked(self, name: str) -> bool:
        if name not in self._failed_providers:
            return False
        elapsed = time.time() - self._fail_timestamps.get(name, 0)
        if elapsed > self.RECOVERY_SECONDS:
            self._failed_providers.discard(name)
            return False
        return True

    def _mark_failed(self, name: str):
        self._failed_providers.add(name)
        self._fail_timestamps[name] = time.time()
