"""Token-Aware Working Memory — Dynamic context management with auto-summarization."""

import logging
from typing import List, Dict, Any, Optional
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.core.memory.working")

class WorkingMemory:
    """Manages active conversation context with token awareness."""

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.messages: List[Dict[str, str]] = []
        self.summary: str = ""

    def add_message(self, role: str, content: str):
        """Add a new message to history."""
        self.messages.append({"role": role, "content": content})
        # Check if we need to summarize
        if self._estimate_tokens() > self.max_tokens:
            asyncio.create_task(self._summarize_old_messages())

    def _estimate_tokens(self) -> int:
        """Rough token estimation (words * 1.3)."""
        text = " ".join([m["content"] for m in self.messages])
        return int(len(text.split()) * 1.3)

    async def _summarize_old_messages(self):
        """Summarize the first half of history into the persistent summary."""
        if len(self.messages) < 10:
            return

        to_summarize = self.messages[:len(self.messages)//2]
        remaining = self.messages[len(self.messages)//2:]
        
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in to_summarize])
        
        prompt = (
            f"Summarize the following conversation history concisely. "
            f"Previous summary: {self.summary}\n\n"
            f"NEW HISTORY TO MERGE:\n{history_text}"
        )
        
        try:
            resp = await router.chat([{"role": "user", "content": prompt}])
            self.summary = resp.content
            self.messages = remaining
            logger.info("Memory summarized to fit token limits.")
        except Exception as e:
            logger.error(f"Memory summarization failed: {e}")

    def get_messages(self) -> List[Dict[str, str]]:
        """Return full context including summary."""
        if not self.summary:
            return self.messages
            
        context_msg = {
            "role": "system",
            "content": f"CONVERSATION SUMMARY SO FAR: {self.summary}"
        }
        return [context_msg] + self.messages

import asyncio
