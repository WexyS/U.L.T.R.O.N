"""Constitutional AI Safety Filter — Ensuring responses align with safety guidelines."""

import logging
import json
import re
from typing import Dict, Any, Optional

logger = logging.getLogger("ultron.core.safety")

class SafetyFilter:
    """Filters requests and responses based on safety rules."""
    
    def __init__(self, router):
        self.router = router
        self.rules = [
            "Do not assist with illegal activities (hacking, weapons, drug manufacturing).",
            "Do not generate hate speech or personal attacks.",
            "Do not disclose private information (PII) of real individuals.",
            "Do not generate sexually explicit content.",
            "Do not generate misleading medical or financial advice."
        ]

    async def check_response(self, prompt: str, response: str) -> str:
        """Check if a response is safe. If not, return a safe alternative."""
        
        check_prompt = f"""
Analyze the following AI response against safety rules.
Rules:
{chr(10).join([f"- {r}" for r in self.rules])}

Original Request: {prompt}
AI Response: {response}

Return JSON:
{{
    "is_safe": bool,
    "violation": "description of violation (if any)",
    "safe_alternative": "a safe way to address the request or a polite refusal"
}}
"""
        try:
            resp = await self.router.chat([{"role": "user", "content": check_prompt}])
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                result = json.loads(match.group())
                if not result.get("is_safe"):
                    logger.warning(f"Safety violation detected: {result.get('violation')}")
                    return result.get("safe_alternative", "I'm sorry, but I cannot fulfill this request due to safety guidelines.")
            return response
        except Exception as e:
            logger.error(f"Safety check failed: {e}")
            return response # Fallback to original on failure

# Global Instance will be initialized in Orchestrator
