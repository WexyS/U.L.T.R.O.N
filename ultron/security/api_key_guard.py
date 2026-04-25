"""API Key Guard — structlog processor that masks secrets in log output.

Detects common API key patterns (OpenAI, Groq, Gemini, HuggingFace, etc.)
and replaces them with masked versions before they reach any log sink.

Usage with structlog:
    import structlog
    from ultron.security.api_key_guard import APIKeyMaskingProcessor

    structlog.configure(
        processors=[
            APIKeyMaskingProcessor(),
            structlog.dev.ConsoleRenderer(),
        ],
    )
"""

import re
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("ultron.security.api_key_guard")

# ── Patterns for known API key formats ─────────────────────────────────
_KEY_PATTERNS: List[re.Pattern] = [
    re.compile(r"(sk-[a-zA-Z0-9]{20,})"),                     # OpenAI
    re.compile(r"(sk-or-v1-[a-zA-Z0-9]{40,})"),                # OpenRouter
    re.compile(r"(sk-ant-[a-zA-Z0-9-]{40,})"),                 # Anthropic
    re.compile(r"(gsk_[a-zA-Z0-9]{20,})"),                     # Groq
    re.compile(r"(AIzaSy[a-zA-Z0-9_-]{33,})"),                 # Google/Gemini
    re.compile(r"(hf_[a-zA-Z0-9]{20,})"),                      # HuggingFace
    re.compile(r"(xai-[a-zA-Z0-9]{20,})"),                     # xAI/Grok
    re.compile(r"(Bearer\s+[a-zA-Z0-9._-]{20,})"),             # Bearer tokens
    re.compile(r"(ghp_[a-zA-Z0-9]{36,})"),                     # GitHub PAT
    re.compile(r"(tvly-[a-zA-Z0-9]{20,})"),                    # Tavily
    re.compile(r"([a-zA-Z0-9]{32,})", re.IGNORECASE),          # Fallback: long hex strings
]

# The fallback (last pattern) is aggressive — only use on values, not keys
_AGGRESSIVE_PATTERN = _KEY_PATTERNS[-1]
_SAFE_PATTERNS = _KEY_PATTERNS[:-1]

# ── Known safe values that should NOT be masked ──────────────────────────
_SAFE_VALUES = frozenset({
    "http://localhost:11434",
    "http://127.0.0.1:11434",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "qwen2.5:14b",
    "qwen2.5-coder:14b",
    "qwen2.5-coder:7b",
})


def mask_api_key(value: str, visible_chars: int = 4) -> str:
    """Mask a single API key string, showing only first and last N chars.

    Args:
        value: The string potentially containing API keys.
        visible_chars: Number of characters to keep visible at each end.

    Returns:
        Masked string if a pattern matches, original string otherwise.
    """
    if not isinstance(value, str) or len(value) < 12:
        return value

    if value in _SAFE_VALUES:
        return value

    for pattern in _SAFE_PATTERNS:
        match = pattern.search(value)
        if match:
            key = match.group(1)
            if len(key) > visible_chars * 2 + 4:
                masked = f"{key[:visible_chars]}****{key[-visible_chars:]}"
                return value.replace(key, masked)

    return value


def _deep_mask(obj: Any, _depth: int = 0) -> Any:
    """Recursively mask API keys in nested data structures.

    Supports: str, dict, list, tuple. Stops at depth 10 to prevent cycles.
    """
    if _depth > 10:
        return obj

    if isinstance(obj, str):
        return mask_api_key(obj)
    elif isinstance(obj, dict):
        return {k: _deep_mask(v, _depth + 1) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        masked = [_deep_mask(item, _depth + 1) for item in obj]
        return type(obj)(masked)
    return obj


class APIKeyMaskingProcessor:
    """structlog processor that masks API keys in all log event values.

    Example:
        >>> proc = APIKeyMaskingProcessor()
        >>> proc(None, None, {"api_key": "sk-1234567890abcdefghij"})
        {'api_key': 'sk-1****ghij'}
    """

    def __call__(
        self,
        logger_instance: Any,
        method_name: str,
        event_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process log event and mask any API keys found in values."""
        return _deep_mask(event_dict)


# ── Environment variable scanner ─────────────────────────────────────────

def scan_env_for_leaked_keys(env_dict: Dict[str, str]) -> List[str]:
    """Scan environment variables and return names of vars that contain API keys.

    Useful for startup validation — warn if keys are in unexpected places.
    """
    suspicious = []
    key_hints = ("key", "token", "secret", "password", "pass", "api")

    for var_name, var_value in env_dict.items():
        name_lower = var_name.lower()
        if any(hint in name_lower for hint in key_hints):
            if var_value and len(var_value) > 8:
                suspicious.append(var_name)

    return suspicious
