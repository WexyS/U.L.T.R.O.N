"""Memory system tests — WorkingMemory, LongTermMemory, ProceduralMemory."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import aiosqlite
import pytest

from ultron.memory.working_memory import WorkingMemory, Message
from ultron.memory.procedural_memory import ProceduralMemory, Procedure


# ===========================================================================
# WorkingMemory tests (pure synchronous — no heavy deps)
# ===========================================================================

class TestWorkingMemory:
    """Tests for the short-term WorkingMemory component."""

    def test_max_messages(self) -> None:
        """Add 25 messages; verify the last 20 are retained."""
        wm = WorkingMemory(max_messages=20, max_tokens=999_999)
        for i in range(25):
            wm.add("user", f"message-{i}")

        msgs = wm.get_messages()
        # deque maxlen = 20*2 = 40, so all 25 stored, no truncation
        assert len(msgs) == 25
        # Verify the last messages are present
        contents = [m.content for m in msgs]
        assert "message-24" in contents
        assert "message-0" in contents

    def test_max_messages_truncation(self) -> None:
        """When the deque's effective capacity is reached, old messages drop."""
        wm = WorkingMemory(max_messages=3, max_tokens=999_999)
        # deque maxlen = 3*2 = 6
        for i in range(10):
            wm.add("user", f"msg-{i}")
        msgs = wm.get_messages()
        # deque(maxlen=6) keeps last 6
        assert len(msgs) == 6
        assert msgs[0].content == "msg-4"
        assert msgs[-1].content == "msg-9"

    def test_token_count(self) -> None:
        """Verify token counting uses the fallback when tiktoken is absent."""
        wm = WorkingMemory(max_messages=20, max_tokens=4000)
        wm.add("user", "hello world")
        # Fallback: 4 chars ≈ 1 token. "hello world" = 11 chars → 2 tokens
        count = wm.token_count()
        assert count >= 1

    def test_clear(self) -> None:
        """Verify clear empties the deque."""
        wm = WorkingMemory(max_messages=20, max_tokens=4000)
        wm.add("user", "hello")
        wm.add("assistant", "hi")
        assert len(wm.get_messages()) == 2
        wm.clear()
        assert len(wm.get_messages()) == 0

    def test_to_messages(self) -> None:
        """Verify output format is list of dicts with role/content."""
        wm = WorkingMemory(max_messages=20, max_tokens=999_999)
        wm.add("user", "Hello!")
        wm.add("assistant", "Hi there!")
        wm.add("user", "How are you?")

        result = wm.to_messages()
        assert isinstance(result, list)
        assert len(result) == 3
        for item in result:
            assert isinstance(item, dict)
            assert "role" in item
            assert "content" in item
        assert result[0] == {"role": "user", "content": "Hello!"}
        assert result[1] == {"role": "assistant", "content": "Hi there!"}
        assert result[2] == {"role": "user", "content": "How are you?"}

    def test_stats(self) -> None:
        """Verify stats returns correct structure."""
        wm = WorkingMemory(max_messages=20, max_tokens=4000)
        wm.add("user", "test")
        stats = wm.stats()
        assert stats["message_count"] == 1
        assert stats["max_messages"] == 20
        assert stats["max_tokens"] == 4000
        assert "token_count" in stats

    def test_apply_summary(self) -> None:
        """Verify apply_summary prepends a summary message."""
        wm = WorkingMemory(max_messages=20, max_tokens=999_999)
        wm.add("user", "part 1")
        wm.add("assistant", "reply 1")
        wm.add("user", "part 2")
        wm.add("assistant", "reply 2")

        wm.apply_summary("Brief summary of earlier chat")
        msgs = wm.get_messages()
        assert msgs[0].role == "system"
        assert "summary" in msgs[0].content.lower()

    def test_message_dataclass(self) -> None:
        """Verify Message dataclass works correctly."""
        msg = Message(role="user", content="test", metadata={"key": "val"})
        assert msg.role == "user"
        assert msg.content == "test"
        assert msg.metadata == {"key": "val"}

    def test_message_default_metadata(self) -> None:
        """Verify Message metadata defaults to empty dict."""
        msg = Message(role="system", content="init")
        assert msg.metadata == {}


# ===========================================================================
# LongTermMemory tests (async, with mocked ChromaDB/embeddings)
# ===========================================================================

@pytest.fixture()
def mock_embedder() -> MagicMock:
    """Mock embedding model that returns a deterministic vector."""
    m = MagicMock()
    m.encode = MagicMock(return_value=[0.1] * 384)
    return m


@pytest.fixture()
def ltm_db_path(tmp_path: Path) -> Path:
    """Provide a temp path for the LTM database."""
    return tmp_path / "test_ltm.db"


class TestLongTermMemory:
    """Tests for the LongTermMemory SQLite-backed component.

    ChromaDB and embedding model are mocked out to keep tests fast.
    """

    async def _create_ltm_tables(self, db_path: Path) -> None:
        """Create LTM tables directly (bypassing full initialization)."""
        async with aiosqlite.connect(str(db_path)) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA foreign_keys=ON")
            await db.execute(
                """CREATE TABLE IF NOT EXISTS episodes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    summary     TEXT NOT NULL,
                    tags        TEXT NOT NULL DEFAULT '[]',
                    importance  REAL NOT NULL DEFAULT 0.5,
                    decay       REAL NOT NULL DEFAULT 90.0
                )"""
            )
            await db.execute(
                """CREATE TABLE IF NOT EXISTS facts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    content     TEXT NOT NULL,
                    source      TEXT NOT NULL DEFAULT '',
                    confidence  REAL NOT NULL DEFAULT 1.0,
                    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                )"""
            )
            await db.execute(
                """CREATE TABLE IF NOT EXISTS entities (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL UNIQUE,
                    type        TEXT NOT NULL DEFAULT 'general',
                    attributes  TEXT NOT NULL DEFAULT '{}',
                    last_seen   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                )"""
            )
            await db.commit()

    async def test_store_and_recall_episode(self, ltm_db_path: Path) -> None:
        """Store an episode and verify it exists in the database."""
        await self._create_ltm_tables(ltm_db_path)

        # Insert directly
        async with aiosqlite.connect(str(ltm_db_path)) as db:
            cursor = await db.execute(
                "INSERT INTO episodes (summary, tags, importance, decay) VALUES (?, ?, ?, ?)",
                ("Test episode about Python programming", json.dumps(["python", "coding"]), 0.8, 90.0),
            )
            await db.commit()
            episode_id = cursor.lastrowid

        assert episode_id is not None
        assert episode_id > 0

        # Verify via direct DB query
        async with aiosqlite.connect(str(ltm_db_path)) as db:
            cursor = await db.execute(
                "SELECT summary, tags, importance FROM episodes WHERE id=?",
                (episode_id,),
            )
            row = await cursor.fetchone()
            assert row is not None
            assert "Python programming" in row[0]
            tags = json.loads(row[1])
            assert "python" in tags
            assert row[2] == pytest.approx(0.8)

    async def test_store_fact(self, ltm_db_path: Path) -> None:
        """Store a fact and verify it exists in the database."""
        await self._create_ltm_tables(ltm_db_path)

        async with aiosqlite.connect(str(ltm_db_path)) as db:
            cursor = await db.execute(
                "INSERT INTO facts (content, source, confidence) VALUES (?, ?, ?)",
                ("Python is a programming language", "general knowledge", 0.95),
            )
            await db.commit()
            fact_id = cursor.lastrowid

        assert fact_id is not None
        assert fact_id > 0

        async with aiosqlite.connect(str(ltm_db_path)) as db:
            cursor = await db.execute(
                "SELECT content, source, confidence FROM facts WHERE id=?",
                (fact_id,),
            )
            row = await cursor.fetchone()
            assert row is not None
            assert "Python" in row[0]
            assert row[1] == "general knowledge"
            assert row[2] == pytest.approx(0.95)

    async def test_entity_storage(self, ltm_db_path: Path) -> None:
        """Store an entity and retrieve it."""
        await self._create_ltm_tables(ltm_db_path)

        async with aiosqlite.connect(str(ltm_db_path)) as db:
            await db.execute(
                "INSERT INTO entities (name, type, attributes) VALUES (?, ?, ?)",
                ("Alice", "person", json.dumps({"age": 30, "city": "New York"})),
            )
            await db.commit()

        # Retrieve
        async with aiosqlite.connect(str(ltm_db_path)) as db:
            cursor = await db.execute(
                "SELECT id, name, type, attributes, last_seen FROM entities WHERE name=?",
                ("Alice",),
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[1] == "Alice"
            assert row[2] == "person"
            attrs = json.loads(row[3])
            assert attrs.get("age") == 30

    async def test_entity_upsert(self, ltm_db_path: Path) -> None:
        """Storing an entity with the same name updates it."""
        await self._create_ltm_tables(ltm_db_path)

        async with aiosqlite.connect(str(ltm_db_path)) as db:
            await db.execute(
                "INSERT INTO entities (name, type, attributes) VALUES (?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET type=excluded.type, attributes=excluded.attributes",
                ("Bob", "person", json.dumps({"role": "friend"})),
            )
            await db.execute(
                "INSERT INTO entities (name, type, attributes) VALUES (?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET type=excluded.type, attributes=excluded.attributes",
                ("Bob", "person", json.dumps({"role": "colleague"})),
            )
            await db.commit()

        async with aiosqlite.connect(str(ltm_db_path)) as db:
            cursor = await db.execute("SELECT attributes FROM entities WHERE name=?", ("Bob",))
            row = await cursor.fetchone()
            assert row is not None
            attrs = json.loads(row[0])
            assert attrs["role"] == "colleague"

    async def test_forget_old_episodes(self, ltm_db_path: Path) -> None:
        """Old episodes with low importance should be decayed or deleted."""
        await self._create_ltm_tables(ltm_db_path)

        # Insert an old episode (100 days ago)
        old_ts = (datetime.now(timezone.utc) - timedelta(days=100)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        async with aiosqlite.connect(str(ltm_db_path)) as db:
            await db.execute(
                "INSERT INTO episodes (timestamp, summary, tags, importance, decay) "
                "VALUES (?, ?, ?, ?, ?)",
                (old_ts, "Old low-importance episode", "[]", 0.1, 30.0),
            )
            # Insert a recent episode
            await db.execute(
                "INSERT INTO episodes (summary, tags, importance, decay) VALUES (?, ?, ?, ?)",
                ("Recent important episode", json.dumps(["recent"]), 0.9, 90.0),
            )
            await db.commit()

        # Apply decay logic
        async with aiosqlite.connect(str(ltm_db_path)) as db:
            rows = await db.execute(
                "SELECT id, importance, timestamp, decay FROM episodes"
            )
            for row in await rows.fetchall():
                eid, importance, ts, decay = row
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
                effective_decay = decay if decay else 90.0
                new_importance = importance * math.exp(-age_days / effective_decay)

                if new_importance < 0.05:
                    await db.execute("DELETE FROM episodes WHERE id=?", (eid,))
                else:
                    await db.execute(
                        "UPDATE episodes SET importance=? WHERE id=?",
                        (round(new_importance, 6), eid),
                    )
            await db.commit()

        # Verify old episode was deleted
        async with aiosqlite.connect(str(ltm_db_path)) as db:
            cursor = await db.execute(
                "SELECT summary FROM episodes WHERE summary LIKE '%Old%'"
            )
            rows = await cursor.fetchall()
            assert len(rows) == 0  # Old episode should be deleted

    async def test_forget_old_facts(self, ltm_db_path: Path) -> None:
        """Facts with old timestamps should decay or be deleted."""
        await self._create_ltm_tables(ltm_db_path)

        old_ts = (datetime.now(timezone.utc) - timedelta(days=100)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        async with aiosqlite.connect(str(ltm_db_path)) as db:
            await db.execute(
                "INSERT INTO facts (content, source, confidence, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("Old fact about something", "test", 0.1, old_ts, old_ts),
            )
            await db.commit()

        # Apply decay
        async with aiosqlite.connect(str(ltm_db_path)) as db:
            rows = await db.execute(
                "SELECT id, confidence, created_at FROM facts"
            )
            for row in await rows.fetchall():
                fid, confidence, ts = row
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
                new_confidence = confidence * math.exp(-age_days / 90.0)

                if new_confidence < 0.05:
                    await db.execute("DELETE FROM facts WHERE id=?", (fid,))
                else:
                    await db.execute(
                        "UPDATE facts SET confidence=? WHERE id=?",
                        (round(new_confidence, 6), fid),
                    )
            await db.commit()

        async with aiosqlite.connect(str(ltm_db_path)) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM facts")
            count = (await cursor.fetchone())[0]
            assert count == 0  # Old fact should be deleted

    async def test_fts_escape(self) -> None:
        """Verify special characters are escaped in FTS5 queries."""
        from ultron.memory.long_term_memory import LongTermMemory
        escaped = LongTermMemory._fts_escape('test "query"')
        assert '"' in escaped


# ===========================================================================
# ProceduralMemory tests (async SQLite-backed)
# ===========================================================================

class TestProceduralMemory:
    """Tests for the ProceduralMemory SQLite-backed component."""

    @pytest.fixture()
    async def pm(self, tmp_path: Path) -> ProceduralMemory:
        """Create a ProceduralMemory instance backed by a temp SQLite DB."""
        db_path = str(tmp_path / "test_procedures.db")
        pm = ProceduralMemory()
        await pm.initialize(db_path=db_path)
        yield pm
        await pm.close()

    async def test_store_and_retrieve_procedure(self, pm: ProceduralMemory) -> None:
        """Store a procedure and retrieve it by fuzzy match."""
        proc_id = await pm.store_procedure(
            trigger="How to create a Python virtual environment",
            steps=[
                "Run: python -m venv myenv",
                "Activate: source myenv/bin/activate",
                "Install packages: pip install -r requirements.txt",
            ],
            category="setup",
            tags=["python", "venv", "environment"],
        )
        assert proc_id is not None
        assert proc_id > 0

        results = await pm.get_best_procedure("virtual environment python")
        assert len(results) >= 1
        assert results[0].trigger == "How to create a Python virtual environment"
        assert len(results[0].steps) == 3
        assert results[0].category == "setup"
        assert "python" in results[0].tags

    async def test_update_success_rate(self, pm: ProceduralMemory) -> None:
        """Record success/failure and verify EMA update."""
        trigger = "Deploy to production"
        await pm.store_procedure(
            trigger=trigger,
            steps=["Step 1", "Step 2"],
            category="deploy",
        )

        # First success: rate = 0.3 * 1.0 + 0.7 * 0.0 = 0.3
        await pm.update_success_rate(trigger, success=True)
        procs = await pm.list_procedures()
        deploy_proc = next(p for p in procs if p.trigger == trigger)
        assert deploy_proc.success_rate == pytest.approx(0.3)
        assert deploy_proc.uses == 1

        # Second success: rate = 0.3 * 1.0 + 0.7 * 0.3 = 0.51
        await pm.update_success_rate(trigger, success=True)
        procs = await pm.list_procedures()
        deploy_proc = next(p for p in procs if p.trigger == trigger)
        assert deploy_proc.success_rate == pytest.approx(0.51)
        assert deploy_proc.uses == 2

        # Failure: rate = 0.3 * 0.0 + 0.7 * 0.51 = 0.357
        await pm.update_success_rate(trigger, success=False)
        procs = await pm.list_procedures()
        deploy_proc = next(p for p in procs if p.trigger == trigger)
        assert deploy_proc.success_rate == pytest.approx(0.357)
        assert deploy_proc.uses == 3

    async def test_update_success_rate_nonexistent(self, pm: ProceduralMemory) -> None:
        """Updating a non-existent trigger should be a no-op (no exception)."""
        await pm.update_success_rate("nonexistent trigger", success=True)
        # Should not raise

    async def test_get_best_procedure(self, pm: ProceduralMemory) -> None:
        """Multiple procedures — return best ranked by score * similarity."""
        await pm.store_procedure(
            trigger="Send an email to a colleague",
            steps=["Open email client", "Compose", "Send"],
            category="communication",
        )
        await pm.store_procedure(
            trigger="Schedule a meeting",
            steps=["Open calendar", "Create event", "Invite attendees"],
            category="communication",
        )
        await pm.store_procedure(
            trigger="Send email with attachment",
            steps=["Open email", "Attach file", "Send"],
            category="communication",
        )

        # Record uses to affect ranking
        await pm.update_success_rate("Send email with attachment", True)
        await pm.update_success_rate("Send email with attachment", True)
        await pm.update_success_rate("Send email with attachment", True)

        results = await pm.get_best_procedure("email attachment")
        assert len(results) >= 1
        # "Send email with attachment" should rank highest due to
        # higher success_rate * uses * similarity
        assert results[0].trigger == "Send email with attachment"

    async def test_get_best_procedure_no_match(self, pm: ProceduralMemory) -> None:
        """Query with no matching procedures returns empty list."""
        await pm.store_procedure(
            trigger="Cook pasta",
            steps=["Boil water", "Add pasta", "Drain"],
            category="cooking",
        )
        results = await pm.get_best_procedure("quantum physics equations")
        assert isinstance(results, list)

    async def test_list_procedures(self, pm: ProceduralMemory) -> None:
        """List all procedures and filter by category."""
        await pm.store_procedure(
            trigger="Task A", steps=["Step 1"], category="cat1",
        )
        await pm.store_procedure(
            trigger="Task B", steps=["Step 1"], category="cat2",
        )
        await pm.store_procedure(
            trigger="Task C", steps=["Step 1"], category="cat1",
        )

        all_procs = await pm.list_procedures()
        assert len(all_procs) == 3

        cat1_procs = await pm.list_procedures(category="cat1")
        assert len(cat1_procs) == 2

        cat2_procs = await pm.list_procedures(category="cat2")
        assert len(cat2_procs) == 1

    async def test_delete_procedure(self, pm: ProceduralMemory) -> None:
        """Delete a procedure by ID."""
        proc_id = await pm.store_procedure(
            trigger="Delete me", steps=["Step 1"],
        )
        assert await pm.delete_procedure(proc_id) is True

        remaining = await pm.list_procedures()
        assert all(p.trigger != "Delete me" for p in remaining)

    async def test_delete_nonexistent_procedure(self, pm: ProceduralMemory) -> None:
        """Deleting a non-existent procedure returns False."""
        result = await pm.delete_procedure(99999)
        assert result is False

    async def test_procedure_to_dict(self, pm: ProceduralMemory) -> None:
        """Verify Procedure.to_dict() returns correct structure."""
        proc_id = await pm.store_procedure(
            trigger="Test procedure",
            steps=["Step 1", "Step 2"],
            category="test",
            tags=["a", "b"],
        )
        procs = await pm.list_procedures()
        proc = next(p for p in procs if p.id == proc_id)
        d = proc.to_dict()
        assert d["id"] == proc_id
        assert d["trigger"] == "Test procedure"
        assert d["steps"] == ["Step 1", "Step 2"]
        assert d["category"] == "test"
        assert d["tags"] == ["a", "b"]
        assert "success_rate" in d
        assert "uses" in d
        assert "created_at" in d

    async def test_live_stats(self, pm: ProceduralMemory) -> None:
        """Verify live_stats returns correct structure."""
        await pm.store_procedure(
            trigger="Task A", steps=["Step 1"], category="cat1",
        )
        await pm.update_success_rate("Task A", True)

        stats = await pm.live_stats()
        assert stats["count"] == 1
        assert stats["avg_success_rate"] > 0
        assert stats["total_uses"] >= 1
        assert "cat1" in stats["category_counts"]

    async def test_record_attempt(self, pm: ProceduralMemory) -> None:
        """record_attempt is a convenience wrapper around update_success_rate."""
        await pm.store_procedure(
            trigger="Test attempt", steps=["Step 1"],
        )
        await pm.record_attempt("Test attempt", success=True)

        procs = await pm.list_procedures()
        proc = next(p for p in procs if p.trigger == "Test attempt")
        assert proc.uses == 1
        assert proc.success_rate > 0

    async def test_procedure_from_row(self) -> None:
        """Verify Procedure.from_row correctly parses a raw SQLite row."""
        row = (
            1,
            "Test trigger",
            json.dumps(["step1", "step2"]),
            0.75,
            10,
            "2024-01-01T00:00:00+00:00",
            "2024-01-02T00:00:00+00:00",
            "test",
            json.dumps(["tag1"]),
        )
        proc = Procedure.from_row(row)
        assert proc.id == 1
        assert proc.trigger == "Test trigger"
        assert proc.steps == ["step1", "step2"]
        assert proc.success_rate == 0.75
        assert proc.uses == 10
        assert proc.category == "test"
        assert proc.tags == ["tag1"]

    async def test_stats_method(self, pm: ProceduralMemory) -> None:
        """stats() returns a dict (synchronous, no DB round-trip)."""
        stats = pm.stats()
        assert isinstance(stats, dict)
        assert "count" in stats
        assert "avg_success_rate" in stats

    async def test_store_procedure_empty_steps(self, pm: ProceduralMemory) -> None:
        """Procedure with empty steps list should still store."""
        proc_id = await pm.store_procedure(
            trigger="Empty procedure",
            steps=[],
        )
        assert proc_id > 0

        procs = await pm.list_procedures()
        proc = next(p for p in procs if p.id == proc_id)
        assert proc.steps == []

    async def test_get_best_procedure_uninitialized_db(self) -> None:
        """get_best_procedure on uninitialized DB returns empty list."""
        pm = ProceduralMemory()
        # Don't call initialize
        results = await pm.get_best_procedure("anything")
        assert results == []

    async def test_live_stats_uninitialized_db(self) -> None:
        """live_stats on uninitialized DB returns defaults."""
        pm = ProceduralMemory()
        stats = await pm.live_stats()
        assert stats["count"] == 0
        assert stats["avg_success_rate"] == 0.0

    async def test_stats_uninitialized_db(self) -> None:
        """stats() on uninitialized PM returns defaults."""
        pm = ProceduralMemory()
        stats = pm.stats()
        assert stats["count"] == 0
        assert stats["avg_success_rate"] == 0.0
