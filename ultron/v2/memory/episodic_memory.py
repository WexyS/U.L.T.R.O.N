"""Episodic Memory for Ultron v3.0 — Chronological event log of experiences."""

import aiosqlite
import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger("ultron.memory.episodic")

class EpisodicMemory:
    """Stores the chronological sequence of events and experiences."""

    def __init__(self, db_path: str = "data/memory/episodic.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def _get_db(self):
        """Asenkron veritabanı bağlantısı ve performans ayarları."""
        db = await aiosqlite.connect(self.db_path, timeout=30)
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA cache_size=-32000")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA temp_store=MEMORY")
        await db.execute("PRAGMA mmap_size=268435456")
        return db

    async def initialize(self):
        async with await self._get_db() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    agent_id TEXT,
                    content TEXT NOT NULL,
                    outcome TEXT,
                    metadata TEXT
                )
            """)
            await db.commit()

    async def store(self, event_type: str, content: str, agent_id: str = None, outcome: str = None, metadata: Dict[str, Any] = None):
        """Store a new episode."""
        async with await self._get_db() as db:
            await db.execute(
                "INSERT INTO episodes (timestamp, event_type, agent_id, content, outcome, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), event_type, agent_id, content, outcome, json.dumps(metadata or {}))
            )
            await db.commit()

    async def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent episodes."""
        async with await self._get_db() as db:
            async with db.execute("SELECT * FROM episodes ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": r[0], "timestamp": r[1], "event_type": r[2],
                        "agent_id": r[3], "content": r[4], "outcome": r[5],
                        "metadata": json.loads(r[6])
                    }
                    for r in rows
                ]

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Simple text search over episodes."""
        async with await self._get_db() as db:
            async with db.execute("SELECT * FROM episodes WHERE content LIKE ? OR event_type LIKE ?", (f"%{query}%", f"%{query}%")) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": r[0], "timestamp": r[1], "event_type": r[2],
                        "agent_id": r[3], "content": r[4], "outcome": r[5],
                        "metadata": json.loads(r[6])
                    }
                    for r in rows
                ]
