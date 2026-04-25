"""Fallback chain — tries providers in order, blocks failures temporarily."""
import time
import asyncio
from typing import Optional

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ultron.providers")

from ultron.providers.base import BaseProvider, Message, ProviderResult


class FallbackChain:
    RECOVERY_SECS = 300  # başarısız provider'ı 5dk sonra tekrar dene

    def __init__(self, providers: dict[str, BaseProvider], order: list[str]):
        self.providers = providers
        self.order = order
        self._failed: dict[str, float] = {}  # name → fail timestamp

    async def execute(
        self,
        messages: list[Message],
        model: Optional[str] = None,
    ) -> ProviderResult:
        for name in self.order:
            p = self.providers.get(name)
            if not p:
                continue
            if self._is_blocked(name):
                logger.debug("provider_blocked", provider=name)
                continue
            try:
                if not await asyncio.wait_for(p.is_available(), timeout=5):
                    self._block(name)
                    continue
                result = await asyncio.wait_for(
                    p.chat(messages, model=model),
                    timeout=p.config.timeout,
                )
                logger.info(
                    "provider_ok",
                    provider=name,
                    latency_ms=result.latency_ms,
                )
                return result
            except asyncio.TimeoutError:
                logger.warning("provider_timeout", provider=name)
                self._block(name)
            except Exception as e:
                logger.warning("provider_error", provider=name, error=str(e))
                self._block(name)
        raise RuntimeError(
            "Tüm AI sağlayıcıları başarısız oldu. "
            "Ollama çalışıyor mu? API keyleri .env'de doğru mu?"
        )

    def _is_blocked(self, name: str) -> bool:
        ts = self._failed.get(name)
        if ts is None:
            return False
        if time.time() - ts > self.RECOVERY_SECS:
            del self._failed[name]
            return False
        return True

    def _block(self, name: str):
        self._failed[name] = time.time()
