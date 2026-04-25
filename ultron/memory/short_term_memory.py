"""Short-Term Memory for Ultron v3.0 — Session context and recent history."""

import logging
from collections import deque
from typing import List, Dict, Any

logger = logging.getLogger("ultron.memory.short_term")

class ShortTermMemory:
    """Stores recent session context, limited by count or tokens."""

    def __init__(self, max_size: int = 20):
        self._history = deque(maxlen=max_size)

    def add(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a message to the session history."""
        self._history.append({
            "role": role,
            "content": content,
            "metadata": metadata or {}
        })

    def get_all(self) -> List[Dict[str, Any]]:
        """Retrieve all session messages."""
        return list(self._history)

    def clear(self):
        """Clear session history."""
        self._history.clear()

    def to_prompt_format(self) -> List[Dict[str, str]]:
        """Convert history to LLM-ready format."""
        return [{"role": m["role"], "content": m["content"]} for m in self._history]
