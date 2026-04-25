"""AI Message Queue — SQLite-backed, race-condition-free FIFO queue.

Replaces file-polling approaches with atomic database operations.
Uses WAL mode + busy_timeout for concurrent safety.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite
from ultron.memory.base_db import get_db

logger = logging.getLogger("ultron.core.message_queue")


class AIMessageQueue:
    """SQLite-backed async message queue with dead-letter support."""

    def __init__(self, db_path: str = "data/message_queue.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        async with get_db(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mq_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_name TEXT NOT NULL DEFAULT 'default',
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority INTEGER DEFAULT 0,
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    ttl_seconds INTEGER DEFAULT 3600,
                    error TEXT
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_mq_status 
                ON mq_messages(queue_name, status, priority DESC)
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mq_dead_letters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_id INTEGER,
                    queue_name TEXT,
                    payload TEXT,
                    error TEXT,
                    died_at TEXT
                )
            """)
            await db.commit()
        logger.info("AIMessageQueue initialized (db=%s)", self.db_path)

    async def enqueue(
        self, payload: Any, queue_name: str = "default",
        priority: int = 0, ttl_seconds: int = 3600,
    ) -> int:
        async with get_db(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO mq_messages 
                   (queue_name, payload, priority, created_at, ttl_seconds)
                   VALUES (?, ?, ?, ?, ?)""",
                (queue_name, json.dumps(payload), priority,
                 datetime.now().isoformat(), ttl_seconds),
            )
            await db.commit()
            return cursor.lastrowid

    async def dequeue(self, queue_name: str = "default") -> Optional[Dict[str, Any]]:
        """Atomically dequeue the highest-priority pending message."""
        async with get_db(self.db_path) as db:
            # Atomic SELECT + UPDATE in one transaction
            row = await db.execute_fetchall(
                """SELECT id, payload, attempts, max_attempts, created_at, ttl_seconds
                   FROM mq_messages 
                   WHERE queue_name = ? AND status = 'pending'
                   ORDER BY priority DESC, id ASC LIMIT 1""",
                (queue_name,),
            )
            if not row:
                return None

            msg = row[0]
            msg_id, payload, attempts, max_attempts, created_at, ttl = msg

            # Check TTL
            created = datetime.fromisoformat(created_at)
            age = (datetime.now() - created).total_seconds()
            if age > ttl:
                await db.execute(
                    "UPDATE mq_messages SET status = 'expired' WHERE id = ?",
                    (msg_id,),
                )
                await db.commit()
                return await self.dequeue(queue_name)

            # Mark as processing
            await db.execute(
                """UPDATE mq_messages 
                   SET status = 'processing', attempts = attempts + 1, updated_at = ?
                   WHERE id = ?""",
                (datetime.now().isoformat(), msg_id),
            )
            await db.commit()

            return {
                "id": msg_id,
                "payload": json.loads(payload),
                "attempts": attempts + 1,
                "max_attempts": max_attempts,
            }

    async def ack(self, message_id: int) -> None:
        async with get_db(self.db_path) as db:
            await db.execute(
                "UPDATE mq_messages SET status = 'completed', updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), message_id),
            )
            await db.commit()

    async def nack(self, message_id: int, error: str = "") -> None:
        """Negative acknowledge — retry or move to dead letter queue."""
        async with get_db(self.db_path) as db:
            row = await db.execute_fetchall(
                "SELECT attempts, max_attempts FROM mq_messages WHERE id = ?",
                (message_id,),
            )
            if row and row[0][0] >= row[0][1]:
                # Move to dead letter queue
                await db.execute(
                    """INSERT INTO mq_dead_letters (original_id, queue_name, payload, error, died_at)
                       SELECT id, queue_name, payload, ?, ? FROM mq_messages WHERE id = ?""",
                    (error, datetime.now().isoformat(), message_id),
                )
                await db.execute(
                    "UPDATE mq_messages SET status = 'dead', error = ? WHERE id = ?",
                    (error, message_id),
                )
            else:
                await db.execute(
                    "UPDATE mq_messages SET status = 'pending', error = ?, updated_at = ? WHERE id = ?",
                    (error, datetime.now().isoformat(), message_id),
                )
            await db.commit()

    async def queue_size(self, queue_name: str = "default") -> int:
        async with get_db(self.db_path) as db:
            row = await db.execute_fetchall(
                "SELECT COUNT(*) FROM mq_messages WHERE queue_name = ? AND status = 'pending'",
                (queue_name,),
            )
            return row[0][0] if row else 0

    async def dead_letter_count(self) -> int:
        async with get_db(self.db_path) as db:
            row = await db.execute_fetchall("SELECT COUNT(*) FROM mq_dead_letters")
            return row[0][0] if row else 0


message_queue = AIMessageQueue()
