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


from ultron.memory.context_manager import ContextManager, ScoredMessage


class WorkingMemory:
    def __init__(self, max_messages: int = 50, max_tokens: int = 6000) -> None:
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.context = ContextManager(max_tokens=max_tokens)

    def add(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        # metadata can be used to pass explicit importance
        importance = metadata.get("importance") if metadata else None
        self.context.add_message(role, content, importance=importance)
        if len(self.context.messages) > self.max_messages * 2:
            # Keep the most recent messages within the effective capacity.
            self.context.messages = self.context.messages[-(self.max_messages * 2):]

    def get_messages(self) -> List[Any]:
        # Return ScoredMessage objects for internal use
        return self.context.messages

    async def to_messages_async(self) -> List[Dict[str, str]]:
        """Smart retrieval with compression."""
        return await self.context.get_context()

    def to_messages(self) -> List[Dict[str, str]]:
        """Fallback sync retrieval (no compression)."""
        return [{"role": m.role, "content": m.content} for m in self.context.messages]

    def apply_summary(self, summary_text: str) -> None:
        """Prepend a system summary message to the active context."""
        summary_content = f"[Summary] {summary_text}"
        summary_msg = ScoredMessage(
            role="system",
            content=summary_content,
            importance=1.0,
            tokens=self.context._count_tokens(summary_content),
            summarized=True,
        )
        self.context.messages.insert(0, summary_msg)
        if len(self.context.messages) > self.max_messages * 2:
            self.context.messages = self.context.messages[-(self.max_messages * 2):]

    def token_count(self) -> int:
        return sum(m.tokens for m in self.context.messages)

    def clear(self) -> None:
        self.context.clear()

    def stats(self) -> dict:
        return {
            "message_count": len(self.context.messages),
            "max_messages": self.max_messages,
            "max_tokens": self.max_tokens,
            "token_count": self.token_count(),
        }

