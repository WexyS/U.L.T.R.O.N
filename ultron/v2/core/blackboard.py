"""Shared context / blackboard for inter-agent data sharing."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class BlackboardEntry:
    """A single entry on the blackboard."""
    key: str
    value: Any
    owner: str  # Agent that wrote it
    ttl_seconds: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class Blackboard:
    """Shared memory space for agents to read/write data.

    Unlike the event bus (push-based), the blackboard is pull-based.
    Agents write data, other agents read it when needed.
    """

    def __init__(self, max_entries: int = 500) -> None:
        self._store: dict[str, BlackboardEntry] = {}
        self._lock = asyncio.Lock()
        self._max_entries = max_entries

    async def write(
        self,
        key: str,
        value: Any,
        owner: str,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Write a value to the blackboard."""
        async with self._lock:
            expires_at = None
            if ttl_seconds:
                from datetime import timedelta
                expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

            self._store[key] = BlackboardEntry(
                key=key,
                value=value,
                owner=owner,
                ttl_seconds=ttl_seconds,
                expires_at=expires_at,
            )

            # Evict if over limit
            if len(self._store) > self._max_entries:
                # Remove oldest non-expired entries
                sorted_entries = sorted(self._store.items(), key=lambda x: x[1].created_at)
                for k, v in sorted_entries[:len(self._store) - self._max_entries]:
                    del self._store[k]

            logger.debug("Blackboard write: %s by %s", key, owner)

    async def read(self, key: str, default: Any = None) -> Any:
        """Read a value from the blackboard."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return default
            if entry.is_expired():
                del self._store[key]
                return default
            return entry.value

    async def delete(self, key: str) -> bool:
        """Delete a key from the blackboard."""
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    async def keys(self, prefix: Optional[str] = None) -> list[str]:
        """List all keys, optionally filtered by prefix."""
        async with self._lock:
            # Clean expired
            now = datetime.now()
            expired = [k for k, v in self._store.items() if v.expires_at and now > v.expires_at]
            for k in expired:
                del self._store[k]

            keys = list(self._store.keys())
            if prefix:
                keys = [k for k in keys if k.startswith(prefix)]
            return keys

    async def clear(self, owner: Optional[str] = None) -> int:
        """Clear all entries, optionally by owner."""
        async with self._lock:
            if owner:
                to_delete = [k for k, v in self._store.items() if v.owner == owner]
                for k in to_delete:
                    del self._store[k]
                return len(to_delete)
            else:
                count = len(self._store)
                self._store.clear()
                return count

    async def get_all(self, prefix: Optional[str] = None) -> dict[str, Any]:
        """Get all values as a dict."""
        async with self._lock:
            # Clean expired entries inline — do NOT call self.keys() here,
            # because keys() also acquires self._lock, causing deadlock.
            now = datetime.now()
            expired = [k for k, v in self._store.items() if v.expires_at and now > v.expires_at]
            for k in expired:
                del self._store[k]

            result = {}
            keys = list(self._store.keys())
            if prefix:
                keys = [k for k in keys if k.startswith(prefix)]

            for key in keys:
                entry = self._store[key]
                if not entry.is_expired():
                    result[key] = entry.value
            return result
