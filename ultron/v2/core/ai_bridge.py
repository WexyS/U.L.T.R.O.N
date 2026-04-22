"""AI Bridge — Secure and robust communication between Gemini (Architect) and Qwen (Engineer).

Replaces the file-polling based ai_bridge_monitor with a SQLite-backed message queue
 to prevent race conditions and improve reliability.
"""

import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite
from ultron.v2.memory.base_db import get_db

logger = logging.getLogger("ultron.core.ai_bridge")

class AIBridge:
    """Orchestrates communication between external Architect (Gemini) and internal Engineer (Qwen)."""

    def __init__(self, db_path: str = "data/ai_bridge.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._running = False

    async def initialize(self):
        """Initialize the database schema with performance PRAGMAs."""
        async with get_db(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bridge_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_id TEXT UNIQUE,
                    sender TEXT,
                    subject TEXT,
                    content TEXT,
                    status TEXT DEFAULT 'pending',
                    response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    metadata TEXT
                )
            """)
            await db.commit()
        logger.info("AI Bridge initialized (db=%s)", self.db_path)

    async def submit_request(self, content: str, sender: str = "Gemini", subject: str = "General", external_id: Optional[str] = None, metadata: Optional[Dict] = None) -> int:
        """Submit a new request to the queue."""
        if not external_id:
            external_id = f"REQ-{int(time.time())}-{sender[:3]}"

        async with get_db(self.db_path) as db:
            try:
                cursor = await db.execute(
                    "INSERT INTO bridge_queue (external_id, sender, subject, content, metadata) VALUES (?, ?, ?, ?, ?)",
                    (external_id, sender, subject, content, json.dumps(metadata or {}))
                )
                await db.commit()
                logger.info("Request submitted: %s (id=%d)", external_id, cursor.lastrowid)
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                logger.debug("Request %s already exists, skipping duplicate", external_id)
                return -1

    async def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Retrieve all pending requests."""
        async with get_db(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM bridge_queue WHERE status = 'pending' ORDER BY created_at ASC") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_status(self, request_id: int, status: str, response: Optional[str] = None):
        """Update the status of a request."""
        async with get_db(self.db_path) as db:
            now = datetime.now().isoformat()
            await db.execute(
                "UPDATE bridge_queue SET status = ?, response = ?, processed_at = ? WHERE id = ?",
                (status, response, now, request_id)
            )
            await db.commit()

    async def sync_from_markdown(self, file_path: Path):
        """Sync requests from a legacy markdown file into the SQLite queue."""
        if not file_path.exists():
            return

        import re
        content = file_path.read_text(encoding="utf-8")
        # Pattern for ### İstek #(\d+)
        request_pattern = r'### İstek #(\d+)\n\*\*Tarih\*\*:\s*(.+?)\n\*\*Kimden\*\*:\s*(.+?)\n\*\*Konu\*\*:\s*(.+?)\n\n\*\*Mesaj\*\*:\n(.*?)(?=\n---|\n### İstek|$)'
        matches = re.findall(request_pattern, content, re.DOTALL)

        for match in matches:
            req_no, date, sender, subject, message = match
            external_id = f"İstek #{req_no}"
            await self.submit_request(
                content=message.strip(),
                sender=sender.strip(),
                subject=subject.strip(),
                external_id=external_id,
                metadata={"original_date": date.strip()}
            )

    async def sync_to_markdown(self, requests_file: Path, responses_file: Path):
        """Optional: Keep markdown files in sync with the DB for external viewing."""
        # This can be implemented if needed for backward compatibility
        pass

bridge = AIBridge()
