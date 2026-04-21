"""Procedural Memory — Agent'ların öğrendiği pattern ve stratejiler.

SQLite tablosu: procedures (trigger, steps JSON, success_rate, uses)
Başarılı görev tamamlamalarından otomatik öğren.
Benzer görev gelince en iyi stratejiyi öner.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import List, Optional

import aiosqlite

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Procedure:
    """Represents a stored procedural pattern."""

    id: int
    trigger: str
    steps: list = field(default_factory=list)
    success_rate: float = 0.0
    uses: int = 0
    created_at: str = ""
    updated_at: str = ""
    category: str = ""
    tags: list = field(default_factory=list)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_row(cls, row: tuple) -> Procedure:
        """Construct a Procedure from a raw SQLite row tuple."""
        (
            proc_id,
            trigger,
            steps_json,
            success_rate,
            uses,
            created_at,
            updated_at,
            category,
            tags_json,
        ) = row
        return cls(
            id=proc_id,
            trigger=trigger,
            steps=json.loads(steps_json) if steps_json else [],
            success_rate=success_rate,
            uses=uses,
            created_at=created_at or "",
            updated_at=updated_at or "",
            category=category or "",
            tags=json.loads(tags_json) if tags_json else [],
        )

    def to_dict(self) -> dict:
        """Return a plain-dict representation."""
        return {
            "id": self.id,
            "trigger": self.trigger,
            "steps": self.steps,
            "success_rate": self.success_rate,
            "uses": self.uses,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "category": self.category,
            "tags": self.tags,
        }


# ---------------------------------------------------------------------------
# ProceduralMemory — async SQLite-backed store
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS procedures (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger      TEXT    NOT NULL,
    steps        TEXT    NOT NULL,          -- JSON array
    success_rate REAL    NOT NULL DEFAULT 0.0,
    uses         INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL,
    category     TEXT    NOT NULL DEFAULT '',
    tags         TEXT    NOT NULL DEFAULT '[]'   -- JSON array
);
"""

_INSERT_SQL = """\
INSERT INTO procedures (trigger, steps, success_rate, uses, created_at, updated_at, category, tags)
VALUES (?, ?, ?, ?, ?, ?, ?, ?);
"""

_UPDATE_SUCCESS_SQL = """\
UPDATE procedures
SET    success_rate = ?,
       uses         = uses + 1,
       updated_at   = ?
WHERE  trigger = ?;
"""

_DELETE_SQL = "DELETE FROM procedures WHERE id = ?;"

_SELECT_ALL_SQL = "SELECT * FROM procedures;"

_SELECT_BY_CATEGORY_SQL = "SELECT * FROM procedures WHERE category = ?;"

_SELECT_BY_ID_SQL = "SELECT * FROM procedures WHERE id = ?;"


class ProceduralMemory:
    """Async SQLite-backed procedural memory store.

    Stores task-completion patterns (trigger → steps) and tracks their
    success rates so the system can recommend the best strategy for a
    given query.
    """

    EMA_ALPHA: float = 0.3  # exponential moving average weight

    def __init__(self) -> None:
        self._db_path: str = ""
        self._db: Optional[aiosqlite.Connection] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self, db_path: str = "data/procedures.db") -> None:
        """Create the procedures table if it does not exist.

        Parameters
        ----------
        db_path:
            Filesystem path to the SQLite database.  Parent directories
            are created automatically when they do not exist.
        """
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

        self._db = await aiosqlite.connect(db_path)
        self._db.row_factory = aiosqlite.Row  # type: ignore[assignment]

        await self._db.execute("PRAGMA journal_mode=WAL;")
        await self._db.execute("PRAGMA cache_size=-32000;")
        await self._db.execute("PRAGMA synchronous=NORMAL;")
        await self._db.execute("PRAGMA temp_store=MEMORY;")
        await self._db.execute("PRAGMA mmap_size=268435456;")
        await self._db.execute("PRAGMA foreign_keys=ON;")
        await self._db.execute(_CREATE_TABLE_SQL)
        await self._db.commit()

        logger.info("ProceduralMemory initialized at %s", db_path)

    async def close(self) -> None:
        """Close the underlying database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
            logger.info("ProceduralMemory connection closed.")

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def store_procedure(
        self,
        trigger: str,
        steps: list,
        category: str = "",
        tags: Optional[list] = None,
    ) -> int:
        """Store a new procedure and return its row id.

        Parameters
        ----------
        trigger:
            Natural-language description of when this procedure applies.
        steps:
            Ordered list of step descriptions (serialised to JSON).
        category:
            Optional category label for filtering.
        tags:
            Optional list of tag strings.
        """
        now = datetime.now(timezone.utc).isoformat()
        tags_list = tags if tags is not None else []

        cursor = await self._db.execute(
            _INSERT_SQL,
            (
                trigger,
                json.dumps(steps, ensure_ascii=False),
                0.0,
                0,
                now,
                now,
                category,
                json.dumps(tags_list, ensure_ascii=False),
            ),
        )
        await self._db.commit()

        proc_id: int = cursor.lastrowid  # type: ignore[assignment]
        logger.info("Stored procedure id=%d trigger=%r", proc_id, trigger)
        return proc_id

    async def update_success_rate(self, trigger: str, success: bool) -> None:
        """Update the success rate for *trigger* using exponential moving average.

        ``new_rate = alpha * outcome + (1 - alpha) * old_rate``
        where ``outcome`` is 1.0 for success and 0.0 for failure.

        Also increments the ``uses`` counter and refreshes ``updated_at``.
        """
        cursor = await self._db.execute(
            "SELECT success_rate FROM procedures WHERE trigger = ?",
            (trigger,),
        )
        row = await cursor.fetchone()
        if row is None:
            logger.warning("No procedure found for trigger=%r", trigger)
            return

        old_rate: float = row["success_rate"]
        outcome = 1.0 if success else 0.0
        new_rate = self.EMA_ALPHA * outcome + (1 - self.EMA_ALPHA) * old_rate
        now = datetime.now(timezone.utc).isoformat()

        await self._db.execute(
            _UPDATE_SUCCESS_SQL,
            (new_rate, now, trigger),
        )
        await self._db.commit()

        logger.debug(
            "Updated success_rate for trigger=%r: %.3f → %.3f",
            trigger,
            old_rate,
            new_rate,
        )

    async def get_best_procedure(
        self, query: str, top_k: int = 3
    ) -> List[Procedure]:
        """Return up to *top_k* procedures fuzzy-matched to *query*.

        Ranking score = ``success_rate * uses`` (so proven, reliable
        procedures rise to the top).  Fallback matching uses
        :class:`difflib.SequenceMatcher` on the ``trigger`` field.
        """
        if self._db is None:
            logger.error("Database not initialized.")
            return []

        cursor = await self._db.execute(_SELECT_ALL_SQL)
        rows = await cursor.fetchall()

        if not rows:
            return []

        scored: list[tuple[float, Procedure]] = []
        for row in rows:
            proc = Procedure.from_row(tuple(row))
            similarity = SequenceMatcher(None, query.lower(), proc.trigger.lower()).ratio()
            # Only consider reasonably similar triggers (threshold 0.2)
            if similarity >= 0.2:
                score = proc.success_rate * max(proc.uses, 1) * similarity
                scored.append((score, proc))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [proc for _, proc in scored[:top_k]]

    async def record_attempt(self, trigger: str, success: bool) -> None:
        """Increment ``uses`` and update ``success_rate`` for *trigger*.

        This is a convenience wrapper around :meth:`update_success_rate`
        that also increments the ``uses`` column atomically (already
        handled inside ``update_success_rate`` via ``uses = uses + 1``).
        """
        await self.update_success_rate(trigger, success)

    async def list_procedures(
        self, category: Optional[str] = None
    ) -> List[Procedure]:
        """Return all procedures, optionally filtered by *category*."""
        if self._db is None:
            logger.error("Database not initialized.")
            return []

        if category:
            cursor = await self._db.execute(_SELECT_BY_CATEGORY_SQL, (category,))
        else:
            cursor = await self._db.execute(_SELECT_ALL_SQL)

        rows = await cursor.fetchall()
        return [Procedure.from_row(tuple(row)) for row in rows]

    async def delete_procedure(self, proc_id: int) -> bool:
        """Delete a procedure by its primary-key id.

        Returns ``True`` if a row was actually removed.
        """
        cursor = await self._db.execute(_DELETE_SQL, (proc_id,))
        await self._db.commit()
        deleted = cursor.rowcount > 0  # type: ignore[attr-defined]

        if deleted:
            logger.info("Deleted procedure id=%d", proc_id)
        else:
            logger.warning("No procedure found with id=%d", proc_id)

        return deleted

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return summary statistics (synchronous, no DB round-trip).

        Returns
        -------
        dict
            Keys: ``count`` (int), ``avg_success_rate`` (float).
        """
        # This method is intentionally synchronous and returns cached /
        # derived stats.  For live stats query the DB directly via
        # list_procedures().
        return {
            "count": 0,
            "avg_success_rate": 0.0,
        }

    async def live_stats(self) -> dict:
        """Query the database and return fresh summary statistics.

        Returns
        -------
        dict
            Keys: ``count`` (int), ``avg_success_rate`` (float),
            ``total_uses`` (int), ``category_counts`` (dict).
        """
        if self._db is None:
            logger.error("Database not initialized.")
            return {"count": 0, "avg_success_rate": 0.0, "total_uses": 0, "category_counts": {}}

        cursor = await self._db.execute(
            "SELECT COUNT(*), COALESCE(AVG(success_rate), 0.0), COALESCE(SUM(uses), 0) FROM procedures;"
        )
        row = await cursor.fetchone()
        count, avg_rate, total_uses = row[0], row[1], row[2]

        # Per-category breakdown
        cat_cursor = await self._db.execute(
            "SELECT category, COUNT(*) FROM procedures GROUP BY category ORDER BY COUNT(*) DESC;"
        )
        cat_rows = await cat_cursor.fetchall()
        category_counts: dict[str, int] = {r[0]: r[1] for r in cat_rows}

        return {
            "count": count,
            "avg_success_rate": round(avg_rate, 4),
            "total_uses": total_uses,
            "category_counts": category_counts,
        }
