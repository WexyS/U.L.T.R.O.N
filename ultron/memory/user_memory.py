from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class UserMemory:
    def __init__(self, persist_dir: str = "./data/memory") -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._profile_path = self.persist_dir / "user_profiles.json"
        self._profiles: dict[str, dict[str, Any]] = self._load_profiles()

    def _load_profiles(self) -> dict[str, dict[str, Any]]:
        if not self._profile_path.exists():
            return {}
        try:
            data = json.loads(self._profile_path.read_text(encoding="utf-8"))
            return data.get("profiles", {})
        except Exception:
            return {}

    def _save_profiles(self) -> None:
        self._profile_path.write_text(
            json.dumps({"profiles": self._profiles}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def set_user(self, name: str, interests: list[str] | None = None, **metadata: Any) -> None:
        name = name.strip()
        if not name:
            return
        profile = self._profiles.get(name, {})
        profile["name"] = name
        profile["interests"] = interests if interests is not None else profile.get("interests", [])
        profile["metadata"] = {**profile.get("metadata", {}), **metadata}
        profile["last_seen"] = datetime.now().isoformat()
        self._profiles[name] = profile
        self._save_profiles()

    def get_profile(self, name: str) -> dict[str, Any]:
        return self._profiles.get(name.strip(), {})

    def update_profile(self, name: str, **updates: Any) -> None:
        profile = self._profiles.get(name.strip(), {})
        if not profile:
            profile = {"name": name.strip(), "interests": [], "metadata": {}, "last_seen": datetime.now().isoformat()}
        profile.update(updates)
        profile["last_seen"] = datetime.now().isoformat()
        self._profiles[name.strip()] = profile
        self._save_profiles()

    def list_profiles(self) -> list[dict[str, Any]]:
        return list(self._profiles.values())
