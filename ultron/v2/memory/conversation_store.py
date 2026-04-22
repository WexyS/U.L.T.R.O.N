"""Conversation Store — SQLite-based persistent conversation storage.

Provides backend-side conversation management:
- Full message history with metadata
- Cross-device sync capability
- Search across conversations
- Import/Export (JSON)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A single message in a conversation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = ""
    role: str = "user"       # user, assistant, system
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Conversation:
    """A conversation containing multiple messages."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Chat"
    model: str = "ollama"
    mode: str = "chat"
    message_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "model": self.model,
            "mode": self.mode,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


from ultron.v2.memory.base_db import get_db_sync


class ConversationStore:
    """SQLite-based conversation persistence.

    Thread-safe, supports concurrent access, and provides
    full CRUD operations on conversations and messages.
    """

    def __init__(self, db_path: str = "./data/conversations.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info("ConversationStore initialized (db=%s)", self.db_path)

    def _init_db(self) -> None:
        """Create database schema if not exists."""
        with get_db_sync(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT 'New Chat',
                    model TEXT DEFAULT 'ollama',
                    mode TEXT DEFAULT 'chat',
                    message_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conv_id
                    ON messages(conversation_id);

                CREATE INDEX IF NOT EXISTS idx_messages_created
                    ON messages(created_at);

                CREATE INDEX IF NOT EXISTS idx_conversations_updated
                    ON conversations(updated_at DESC);
            """)

    # ── Conversation CRUD ────────────────────────────────────────────────


    def create_conversation(
        self,
        title: str = "New Chat",
        model: str = "ollama",
        mode: str = "chat",
        metadata: Optional[dict] = None,
    ) -> Conversation:
        """Create a new conversation."""
        conv = Conversation(
            title=title,
            model=model,
            mode=mode,
            metadata=metadata or {},
        )

        with get_db_sync(self.db_path) as conn:
            conn.execute(
                "INSERT INTO conversations (id, title, model, mode, message_count, created_at, updated_at, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (conv.id, conv.title, conv.model, conv.mode, 0,
                 conv.created_at.isoformat(), conv.updated_at.isoformat(),
                 json.dumps(conv.metadata)),
            )

        logger.debug("Conversation created: %s — %s", conv.id[:8], conv.title)
        return conv

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        with get_db_sync(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()

        if not row:
            return None

        return self._row_to_conversation(row)

    def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> list[Conversation]:
        """List conversations, ordered by most recently updated."""
        with get_db_sync(self.db_path) as conn:
            if search:
                rows = conn.execute(
                    "SELECT * FROM conversations WHERE title LIKE ? "
                    "ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                    (f"%{search}%", limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()

        return [self._row_to_conversation(r) for r in rows]

    def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        model: Optional[str] = None,
        mode: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Update conversation properties."""
        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if model is not None:
            updates.append("model = ?")
            params.append(model)
        if mode is not None:
            updates.append("mode = ?")
            params.append(mode)
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(conversation_id)

        with get_db_sync(self.db_path) as conn:
            result = conn.execute(
                f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            return result.rowcount > 0

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        with get_db_sync(self.db_path) as conn:
            result = conn.execute(
                "DELETE FROM conversations WHERE id = ?", (conversation_id,)
            )
            return result.rowcount > 0

    # ── Message CRUD ─────────────────────────────────────────────────────

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> Message:
        """Add a message to a conversation."""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )

        with get_db_sync(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (msg.id, msg.conversation_id, msg.role, msg.content,
                 json.dumps(msg.metadata), msg.created_at.isoformat()),
            )

            # Update conversation
            conn.execute(
                "UPDATE conversations SET message_count = message_count + 1, updated_at = ? "
                "WHERE id = ?",
                (datetime.now().isoformat(), conversation_id),
            )

            # Auto-generate title from first user message
            first_msg = conn.execute(
                "SELECT content FROM messages WHERE conversation_id = ? AND role = 'user' "
                "ORDER BY created_at LIMIT 1",
                (conversation_id,),
            ).fetchone()

            if first_msg:
                auto_title = first_msg["content"][:50]
                if len(first_msg["content"]) > 50:
                    auto_title += "..."
                conn.execute(
                    "UPDATE conversations SET title = ? WHERE id = ? AND title = 'New Chat'",
                    (auto_title, conversation_id),
                )

        return msg

    def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """Get messages for a conversation."""
        with get_db_sync(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? "
                "ORDER BY created_at ASC LIMIT ? OFFSET ?",
                (conversation_id, limit, offset),
            ).fetchall()

        return [self._row_to_message(r) for r in rows]

    def search_messages(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        limit: int = 20,
    ) -> list[Message]:
        """Search messages by content."""
        with get_db_sync(self.db_path) as conn:
            if conversation_id:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE conversation_id = ? AND content LIKE ? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (conversation_id, f"%{query}%", limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE content LIKE ? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (f"%{query}%", limit),
                ).fetchall()

        return [self._row_to_message(r) for r in rows]

    # ── Export/Import ─────────────────────────────────────────────────────

    def export_conversation(self, conversation_id: str) -> dict:
        """Export a conversation with all messages as JSON."""
        conv = self.get_conversation(conversation_id)
        if not conv:
            return {}

        messages = self.get_messages(conversation_id, limit=10000)

        return {
            "conversation": conv.to_dict(),
            "messages": [m.to_dict() for m in messages],
            "exported_at": datetime.now().isoformat(),
            "version": "1.0",
        }

    def import_conversation(self, data: dict) -> Optional[str]:
        """Import a conversation from exported JSON."""
        try:
            conv_data = data.get("conversation", {})
            messages_data = data.get("messages", [])

            conv = self.create_conversation(
                title=conv_data.get("title", "Imported"),
                model=conv_data.get("model", "ollama"),
                mode=conv_data.get("mode", "chat"),
                metadata=conv_data.get("metadata", {}),
            )

            for msg_data in messages_data:
                self.add_message(
                    conversation_id=conv.id,
                    role=msg_data.get("role", "user"),
                    content=msg_data.get("content", ""),
                    metadata=msg_data.get("metadata", {}),
                )

            logger.info("Conversation imported: %s (%d messages)", conv.id[:8], len(messages_data))
            return conv.id
        except Exception as e:
            logger.error("Failed to import conversation: %s", e)
            return None

    # ── Helpers ───────────────────────────────────────────────────────────

    def _row_to_conversation(self, row: sqlite3.Row) -> Conversation:
        return Conversation(
            id=row["id"],
            title=row["title"],
            model=row["model"],
            mode=row["mode"],
            message_count=row["message_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        return Message(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_stats(self) -> dict:
        """Database statistics."""
        with get_db_sync(self.db_path) as conn:
            conv_count = conn.execute("SELECT COUNT(*) as c FROM conversations").fetchone()["c"]
            msg_count = conn.execute("SELECT COUNT(*) as c FROM messages").fetchone()["c"]

        return {
            "conversations": conv_count,
            "messages": msg_count,
            "db_path": str(self.db_path),
            "db_size_mb": round(self.db_path.stat().st_size / (1024 * 1024), 2) if self.db_path.exists() else 0,
        }
