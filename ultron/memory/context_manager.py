"""Token-Aware Context Manager — Smart Memory Compression and Importance Scoring.

Manages the active conversation context by tracking tokens and summarizing
low-importance messages to maintain maximum useful context within LLM limits.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False

logger = logging.getLogger("ultron.memory.context")

@dataclass
class ScoredMessage:
    role: str
    content: str
    importance: float = 0.5  # 0.0 to 1.0
    tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    summarized: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "importance": self.importance,
            "tokens": self.tokens,
            "timestamp": self.timestamp.isoformat(),
            "summarized": self.summarized
        }

class ContextManager:
    def __init__(self, max_tokens: int = 6000, model_name: str = "cl100k_base"):
        self.max_tokens = max_tokens
        self.messages: List[ScoredMessage] = []
        self._encoder = None
        if _TIKTOKEN_AVAILABLE:
            try:
                self._encoder = tiktoken.get_encoding(model_name)
            except Exception:
                pass

    def _count_tokens(self, text: str) -> int:
        if self._encoder:
            return len(self._encoder.encode(text))
        return len(text) // 4  # Approximation

    def add_message(self, role: str, content: str, importance: Optional[float] = None):
        """Add a message and calculate its importance if not provided."""
        if importance is None:
            importance = self._calculate_importance(role, content)
        
        tokens = self._count_tokens(content)
        msg = ScoredMessage(role=role, content=content, importance=importance, tokens=tokens)
        self.messages.append(msg)
        logger.debug(f"Added message: role={role}, tokens={tokens}, importance={importance}")

    def _calculate_importance(self, role: str, content: str) -> float:
        """Heuristic for message importance."""
        if role == "system":
            return 1.0
        
        importance = 0.5
        # Higher importance for technical content, instructions, or facts
        if any(kw in content.lower() for kw in ["how to", "code", "error", "fix", "remember", "always"]):
            importance += 0.3
        
        # Lower importance for greetings or short responses
        if len(content.split()) < 5:
            importance -= 0.2
            
        return max(0.1, min(1.0, importance))

    async def get_context(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Retrieve context messages, summarizing low-importance ones if limit is exceeded."""
        max_t = limit or self.max_tokens
        current_total = sum(m.tokens for m in self.messages)
        
        if current_total <= max_t:
            return [{"role": m.role, "content": m.content} for m in self.messages]

        logger.info(f"Context exceeds limit ({current_total}/{max_t}). Compressing...")
        
        # Sort by importance (highest first)
        scored = sorted(enumerate(self.messages), key=lambda x: x[1].importance, reverse=True)
        
        result_messages = [None] * len(self.messages)
        total_tokens = 0
        
        for original_idx, msg in scored:
            if total_tokens + msg.tokens <= max_t * 0.8:  # Reserve 20% for summaries
                result_messages[original_idx] = msg
                total_tokens += msg.tokens
            else:
                # This message needs to be summarized or dropped
                if msg.importance > 0.4 and not msg.summarized:
                    summary = await self._summarize_content(msg.content)
                    summary_msg = ScoredMessage(
                        role=msg.role,
                        content=f"[Summary: {summary}]",
                        importance=msg.importance,
                        tokens=self._count_tokens(summary),
                        summarized=True
                    )
                    result_messages[original_idx] = summary_msg
                    total_tokens += summary_msg.tokens
                else:
                    # Drop very low importance messages
                    result_messages[original_idx] = None

        # Return non-None messages in chronological order
        final_list = [m for m in result_messages if m is not None]
        return [{"role": m.role, "content": m.content} for m in final_list]

    async def _summarize_content(self, text: str) -> str:
        """
        Placeholder for LLM summarization. 
        In a real implementation, this would call the LLM router.
        """
        if len(text) < 100:
            return text
        return text[:100] + "..."

    def clear(self):
        self.messages.clear()
