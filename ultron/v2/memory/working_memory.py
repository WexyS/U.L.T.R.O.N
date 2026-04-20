"""
WorkingMemory — Kısa süreli aktif konuşma bağlamı.
deque ile son N mesajı tutar (kapasite max_messages * 2), token sınırı için özetleme.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import tiktoken

    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False


@dataclass
class Message:
    """Tek bir konuşma mesajı (metadata ile)."""

    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkingMemory:
    def __init__(self, max_messages: int = 50, max_tokens: int = 32000) -> None:
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self._deque_maxlen = max(1, max_messages * 2)
        self.messages: deque[Message] = deque(maxlen=self._deque_maxlen)
        self._encoder = None
        if _TIKTOKEN_AVAILABLE:
            try:
                self._encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self._encoder = None

    def add(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        self.messages.append(Message(role=role, content=content, metadata=metadata or {}))

    def get_messages(self) -> List[Message]:
        return list(self.messages)

    def to_messages(self) -> List[Dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def token_count(self) -> int:
        total = 0
        for m in self.messages:
            if self._encoder is not None:
                total += len(self._encoder.encode(m.content))
            else:
                # tiktoken yoksa veya encoder yüklenemediyse: ~4 karakter ≈ 1 token
                total += max(1, len(m.content) // 4)
        return total

    def clear(self) -> None:
        self.messages.clear()

    def should_summarize(self, threshold: Optional[int] = None) -> bool:
        th = threshold if threshold is not None else self.max_tokens
        return self.token_count() > th

    def summarize_if_needed(self, summarize_fn: Any = None) -> Optional[dict]:
        """Token sınırı aşıldığında eski mesajları özetle veya kırp."""
        if not self.should_summarize():
            return None

        messages = list(self.messages)
        split = len(messages) // 2
        to_summarize = messages[:split]
        to_keep = messages[split:]

        if summarize_fn is None:
            self.messages = deque(to_keep, maxlen=self._deque_maxlen)
            return {"type": "trimmed", "messages": self.to_messages()}

        return {
            "to_summarize": [m.content for m in to_summarize],
            "to_keep": [{"role": m.role, "content": m.content} for m in to_keep],
        }

    def apply_summary(self, summary: str) -> None:
        messages = list(self.messages)
        split = len(messages) // 2
        self.messages = deque(messages[split:], maxlen=self._deque_maxlen)
        self.messages.appendleft(
            Message(
                role="system",
                content=f"[Conversation summary: {summary}]",
                metadata={},
            )
        )

    def stats(self) -> dict:
        return {
            "message_count": len(self.messages),
            "max_messages": self.max_messages,
            "max_tokens": self.max_tokens,
            "token_count": self.token_count(),
        }
