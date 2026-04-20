from datetime import datetime
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Any
from pydantic import BaseModel
from dataclasses import dataclass


@dataclass
class ProviderStats:
    """Statistics for an LLM provider."""
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
        """Composite health score: 0.0 (dead) to 1.0 (perfect)."""
        if self.total_calls == 0:
            return 1.0
        # Weight: 70% success rate, 30% recency
        recency_bonus = 0.3 if self.last_active and (datetime.now() - self.last_active).total_seconds() < 300 else 0.0
        return 0.7 * self.success_rate + recency_bonus


class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str | list


class ProviderConfig(BaseModel):
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: str
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 60
    priority: int = 99


class ProviderResult(BaseModel):
    content: str
    provider: str
    model: str
    tokens_used: int = 0
    latency_ms: int = 0


class BaseProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.stats = ProviderStats()

    def is_configured(self) -> bool:
        """API key var mı? Yoksa bu provider atlanır."""
        return bool(self.config.api_key) or self.config.name == "ollama"

    @property
    def display_name(self) -> str:
        return f"Ultron-Channel-{self.config.name.capitalize()}"

    def get_model_name(self) -> str:
        return self.config.default_model

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> ProviderResult: ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[Message],
        model: Optional[str] = None,
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    async def is_available(self) -> bool: ...

    @abstractmethod
    async def list_models(self) -> list[str]: ...
