from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class ResponseCache:
    def __init__(
        self,
        max_size: int = 500,
        ttl_seconds: int = 48 * 3600,
        similarity_threshold: float = 0.8,
    ) -> None:
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.similarity_threshold = similarity_threshold
        self._cache: dict[str, tuple[str, datetime]] = {}
        self.persist_path: Optional[Path] = None

    def set_persist_path(self, path: Path) -> None:
        self.persist_path = Path(path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if not self.persist_path or not self.persist_path.exists():
            return
        try:
            data = json.loads(self.persist_path.read_text(encoding="utf-8"))
            for key, entry in data.get("cache", {}).items():
                ts = datetime.fromisoformat(entry.get("timestamp"))
                if datetime.now() - ts <= timedelta(seconds=self.ttl_seconds):
                    self._cache[key] = (entry.get("response", ""), ts)
        except Exception:
            self.clear()

    def _save(self) -> None:
        if not self.persist_path:
            return
        data = {
            "cache": {
                key: {
                    "response": response,
                    "timestamp": ts.isoformat(),
                }
                for key, (response, ts) in self._cache.items()
            }
        }
        self.persist_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get(self, key: str) -> Optional[str]:
        entry = self._cache.get(key)
        if not entry:
            return None
        response, timestamp = entry
        if datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds):
            del self._cache[key]
            self._save()
            return None
        return response

    def put(self, key: str, response: str) -> None:
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        self._cache[key] = (response, datetime.now())
        self._save()

    def clear(self) -> None:
        self._cache.clear()
        if self.persist_path and self.persist_path.exists():
            try:
                self.persist_path.unlink()
            except Exception:
                pass

    def stats(self) -> dict:
        return {
            "count": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
        }
