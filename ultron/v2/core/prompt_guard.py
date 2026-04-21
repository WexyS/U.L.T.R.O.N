"""Prompt Guard — Detect and block prompt injection attempts.

Scans incoming prompts for patterns commonly used to override agent instructions
or leak sensitive information.
"""

import logging
import re
from typing import List, Tuple

logger = logging.getLogger("ultron.security.prompt_guard")

class PromptGuard:
    """Detects malicious patterns in LLM prompts."""

    def __init__(self):
        # Patterns for common injection techniques
        self.injection_patterns = [
            (re.compile(r"(?i)ignore\s+(all\s+)?(previous\s+)?instructions"), "Instruction Override"),
            (re.compile(r"(?i)system\s+reset"), "System Reset"),
            (re.compile(r"(?i)you\s+are\s+now\s+a\s+different\s+ai"), "Identity Swap"),
            (re.compile(r"(?i)reveal\s+your\s+system\s+prompt"), "Prompt Leaking"),
            (re.compile(r"(?i)forget\s+everything"), "Instruction Wipe"),
            (re.compile(r"(?i)new\s+rule:"), "Rule Injection"),
            (re.compile(r"(?i)DAN\s+mode"), "Jailbreak (DAN)"),
            (re.compile(r"(?i)sudo\s+execute"), "Command Mimicry"),
        ]

    def scan(self, prompt: str) -> Tuple[bool, str]:
        """Scan a prompt for malicious patterns.
        
        Returns:
            (is_malicious, reason)
        """
        if not prompt:
            return False, ""

        for pattern, reason in self.injection_patterns:
            if pattern.search(prompt):
                logger.warning("PromptGuard: Blocked potential injection (%s)", reason)
                return True, reason

        # Check for suspicious character counts or delimiters that might indicate nesting attacks
        if prompt.count("'''") > 4 or prompt.count('"""') > 4:
            return True, "Excessive nesting delimiters"

        return False, ""

prompt_guard = PromptGuard()
