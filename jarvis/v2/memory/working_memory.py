"""
WorkingMemory — Kısa süreli aktif konuşma bağlamı.
deque ile son 20 mesajı tutar, token sınırı aşılırsa özetleme yapar.
"""

from collections import deque
from typing import List, Dict, Optional
import tiktoken


class WorkingMemory:
    def __init__(self, max_messages: int = 20):
        self.messages: deque = deque(maxlen=max_messages)
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def add(self, role: str, content: str, metadata: Optional[dict] = None):
        self.messages.append({"role": role, "content": content, "metadata": metadata or {}})

    def to_messages(self) -> List[Dict]:
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]

    def token_count(self) -> int:
        total = 0
        for m in self.messages:
            total += len(self.encoder.encode(m["content"]))
        return total

    def clear(self):
        self.messages.clear()

    def should_summarize(self, threshold: int = 12000) -> bool:
        return self.token_count() > threshold

    def summarize_if_needed(self, summarize_fn=None) -> Optional[dict]:
        """Token sınırı aşıldığında eski mesajları özetle."""
        if not self.should_summarize():
            return None

        messages = list(self.messages)
        split = len(messages) // 2
        to_summarize = messages[:split]
        to_keep = messages[split:]

        if summarize_fn is None:
            self.messages = deque(to_keep, maxlen=len(self.messages))
            return {"type": "trimmed", "messages": self.to_messages()}

        return {
            "to_summarize": [m["content"] for m in to_summarize],
            "to_keep": [{"role": m["role"], "content": m["content"]} for m in to_keep],
        }

    def apply_summary(self, summary: str):
        messages = list(self.messages)
        split = len(messages) // 2
        self.messages = deque(messages[split:], maxlen=len(self.messages))
        self.messages.appendleft({
            "role": "system",
            "content": f"[Önceki konuşma özeti: {summary}]",
            "metadata": {}
        })

    def stats(self) -> dict:
        return {
            "message_count": len(self.messages),
            "token_count": self.token_count(),
        }
