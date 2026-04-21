"""Memory-Aware Context Management — intelligent token counting and summarization.

Ensures that conversation history stays within LLM context limits while 
preserving essential information through recursive summarization.
"""

import logging
import json
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ultron.core.context")

class ContextManager:
    """Manages LLM context windows with intelligent pruning and summarization."""

    def __init__(self, max_tokens: int = 8000, model_name: str = "qwen2.5"):
        self.max_tokens = max_tokens
        self.model_name = model_name
        self._tokenizer = None  # Lazy init

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimation of tokens (4 chars per token on average)."""
        if not text:
            return 0
        return len(text) // 4

    def count_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in a list of messages."""
        total = 0
        for msg in messages:
            total += self._estimate_tokens(msg.get("content", ""))
            total += 10  # Overhead per message
        return total

    async def optimize_context(self, messages: List[Dict[str, str]], llm_router: Any) -> List[Dict[str, str]]:
        """Optimize context by summarizing or pruning old messages if limit is exceeded."""
        current_tokens = self.count_message_tokens(messages)
        
        if current_tokens <= self.max_tokens:
            return messages

        logger.info("Context optimization triggered: %d > %d tokens", current_tokens, self.max_tokens)
        
        # Keep System Prompt and Latest 4 messages intact
        system_prompt = [m for m in messages if m.get("role") == "system"]
        latest_messages = messages[-4:]
        middle_messages = messages[len(system_prompt):-4]
        
        if not middle_messages:
            # If still too long, we must prune older messages even from the 'latest'
            return system_prompt + latest_messages[-2:]

        # Summarize middle part
        summary_prompt = [
            {"role": "system", "content": "Summarize the following conversation history concisely while preserving key facts and decisions."},
            {"role": "user", "content": "\n".join([f"{m['role']}: {m['content']}" for m in middle_messages])}
        ]
        
        try:
            # We use a fast model for summarization
            resp = await llm_router.chat(summary_prompt, max_tokens=500, task_type="cheap")
            summary = resp.content
            
            optimized = system_prompt + [
                {"role": "system", "content": f"Summary of earlier conversation: {summary}"}
            ] + latest_messages
            
            logger.info("Context optimized via summarization.")
            return optimized
        except Exception as e:
            logger.warning("Summarization failed, falling back to pruning: %s", e)
            # Pruning fallback: keep only the most recent N messages that fit
            return system_prompt + messages[-6:]

context_manager = ContextManager()
