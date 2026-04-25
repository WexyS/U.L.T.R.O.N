"""Tests for AI Message Queue."""

import pytest
from ultron.core.ai_message_queue import AIMessageQueue


@pytest.fixture
async def queue(tmp_path):
    q = AIMessageQueue(db_path=str(tmp_path / "test_mq.db"))
    await q.initialize()
    return q


@pytest.mark.asyncio
class TestAIMessageQueue:
    async def test_enqueue_dequeue(self, tmp_path):
        q = AIMessageQueue(db_path=str(tmp_path / "test.db"))
        await q.initialize()
        msg_id = await q.enqueue({"task": "hello"})
        assert msg_id > 0

        msg = await q.dequeue()
        assert msg is not None
        assert msg["payload"]["task"] == "hello"

    async def test_empty_dequeue(self, tmp_path):
        q = AIMessageQueue(db_path=str(tmp_path / "test.db"))
        await q.initialize()
        msg = await q.dequeue()
        assert msg is None

    async def test_ack(self, tmp_path):
        q = AIMessageQueue(db_path=str(tmp_path / "test.db"))
        await q.initialize()
        msg_id = await q.enqueue({"x": 1})
        msg = await q.dequeue()
        await q.ack(msg["id"])
        # After ack, queue should be empty
        assert await q.dequeue() is None

    async def test_nack_retry(self, tmp_path):
        q = AIMessageQueue(db_path=str(tmp_path / "test.db"))
        await q.initialize()
        await q.enqueue({"x": 1})
        msg = await q.dequeue()
        await q.nack(msg["id"], "temporary error")
        # Should be re-available
        retry = await q.dequeue()
        assert retry is not None

    async def test_nack_dead_letter(self, tmp_path):
        q = AIMessageQueue(db_path=str(tmp_path / "test.db"))
        await q.initialize()
        await q.enqueue({"x": 1})
        # Exhaust retries (default max_attempts = 3)
        for i in range(3):
            msg = await q.dequeue()
            if msg:
                await q.nack(msg["id"], f"error {i}")
        # After max attempts, should be dead
        count = await q.dead_letter_count()
        assert count >= 1

    async def test_queue_size(self, tmp_path):
        q = AIMessageQueue(db_path=str(tmp_path / "test.db"))
        await q.initialize()
        await q.enqueue({"a": 1})
        await q.enqueue({"b": 2})
        size = await q.queue_size()
        assert size == 2

    async def test_priority_ordering(self, tmp_path):
        q = AIMessageQueue(db_path=str(tmp_path / "test.db"))
        await q.initialize()
        await q.enqueue({"low": True}, priority=1)
        await q.enqueue({"high": True}, priority=10)
        msg = await q.dequeue()
        assert msg["payload"]["high"] is True
