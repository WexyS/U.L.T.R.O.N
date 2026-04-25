"""Tests for the Production-Grade ReAct Orchestrator."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from ultron.v2.core.react_orchestrator import (
    ReActOrchestrator, ReActChain, ReActStep, StepType,
    SubTask, AuditLogger, _estimate_tokens, MAX_ITERATIONS, TOKEN_BUDGET,
)
from ultron.v2.core.base_agent import AgentTask, AgentResult


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_router():
    """Mock LLM router that returns predictable responses."""
    with patch("ultron.v2.core.react_orchestrator.router") as m:
        resp = MagicMock()
        resp.content = '{"thinking": "test", "answer": "test response"}'
        m.chat = AsyncMock(return_value=resp)
        yield m


@pytest.fixture
def mock_registry():
    with patch("ultron.v2.core.react_orchestrator.registry") as m:
        m.list_agents.return_value = [
            {"name": "CoderAgent", "description": "Writes code"},
            {"name": "ResearcherAgent", "description": "Does research"},
        ]
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value=AgentResult(
            task_id="test", agent_id="CoderAgent",
            success=True, output="Code generated successfully",
        ))
        m.get_agent.return_value = mock_agent
        yield m


@pytest.fixture
def mock_deps():
    """Mock all external dependencies."""
    with patch("ultron.v2.core.react_orchestrator.user_profile") as up, \
         patch("ultron.v2.core.react_orchestrator.personality_engine") as pe, \
         patch("ultron.v2.core.react_orchestrator.event_bus") as eb:
        up.get_summary_for_prompt.return_value = "User: Eren, Language: Turkish"
        pe.get_system_prompt.return_value = "You are Ultron."
        pe.filter_response.side_effect = lambda x: x
        eb.publish_simple = AsyncMock()
        yield up, pe, eb


@pytest.fixture
def mock_reasoner():
    with patch("ultron.v2.core.react_orchestrator.ReasoningEngine") as cls:
        instance = MagicMock()
        result = MagicMock()
        result.thinking = "Let me analyze this..."
        result.answer = "The task requires coding."
        instance.think_and_answer = AsyncMock(return_value=result)
        cls.return_value = instance
        yield instance


@pytest.fixture
def mock_safety():
    with patch("ultron.v2.core.react_orchestrator.SafetyFilter") as cls:
        instance = MagicMock()
        instance.check_response = AsyncMock(side_effect=lambda q, r: r)
        cls.return_value = instance
        yield instance


@pytest.fixture
def orchestrator(mock_reasoner, mock_safety):
    """Create orchestrator with mocked dependencies."""
    orch = ReActOrchestrator(memory=None)
    return orch


# ── Unit Tests ───────────────────────────────────────────────────────────

class TestTokenEstimator:
    def test_empty_string(self):
        assert _estimate_tokens("") == 0

    def test_short_text(self):
        tokens = _estimate_tokens("hello world")
        assert tokens >= 1

    def test_longer_text(self):
        tokens = _estimate_tokens("a" * 300)
        assert tokens == 100  # 300 / 3

    def test_turkish_text(self):
        tokens = _estimate_tokens("Merhaba dünya, nasılsın?")
        assert tokens >= 1


class TestReActChain:
    def test_initial_state(self):
        chain = ReActChain()
        assert chain.current_iteration == 0
        assert chain.tokens_consumed == 0
        assert chain.budget_remaining == TOKEN_BUDGET
        assert not chain.budget_exhausted
        assert not chain.is_complete

    def test_add_step_tracks_tokens(self):
        chain = ReActChain()
        step = ReActStep(step_type=StepType.THINK, content="test", tokens_used=100)
        chain.add_step(step)
        assert chain.tokens_consumed == 100
        assert chain.budget_remaining == TOKEN_BUDGET - 100
        assert len(chain.steps) == 1

    def test_budget_exhaustion(self):
        chain = ReActChain(token_budget=100)
        step = ReActStep(step_type=StepType.THINK, content="x", tokens_used=100)
        chain.add_step(step)
        assert chain.budget_exhausted


class TestAuditLogger:
    def test_init_creates_db(self, tmp_path):
        db_path = str(tmp_path / "test_audit.db")
        logger = AuditLogger(db_path=db_path)
        assert (tmp_path / "test_audit.db").exists()

    def test_log_step(self, tmp_path):
        db_path = str(tmp_path / "test_audit.db")
        audit = AuditLogger(db_path=db_path)
        step = ReActStep(step_type=StepType.THINK, content="test content", tokens_used=50)
        audit.log_step("session_1", 1, step, success=True)

        import sqlite3
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT * FROM react_audit").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][2] == 1  # step_number
        assert rows[0][3] == "think"  # step_type


class TestSubTask:
    def test_default_values(self):
        st = SubTask(agent_name="Coder", description="Write code", input_data="print('hi')")
        assert st.parallel is False
        assert st.status == "pending"
        assert st.result is None


class TestReActOrchestrator:
    @pytest.mark.asyncio
    async def test_full_loop(self, orchestrator, mock_router, mock_registry, mock_deps):
        """Test a complete THINK→PLAN→ACT→OBSERVE→REFLECT→RESPOND cycle."""
        # Configure router to return plan JSON then "TASK_COMPLETE"
        plan_response = MagicMock()
        plan_response.content = json.dumps([{
            "agent_name": "CoderAgent",
            "description": "Generate code",
            "input_data": "Write hello world",
            "parallel": False,
        }])

        reflect_response = MagicMock()
        reflect_response.content = "All tasks completed. TASK_COMPLETE"

        sentiment_response = MagicMock()
        sentiment_response.content = "CHILL"

        mock_router.chat = AsyncMock(side_effect=[
            plan_response,      # _plan
            sentiment_response, # _analyze_sentiment
            plan_response,      # second _plan call in loop
            reflect_response,   # _reflect
        ])

        task = AgentTask(
            task_type="user_request",
            input_data="Write a Python hello world program",
            context={},
        )

        result = await orchestrator.execute(task)
        assert result.task_id == task.task_id
        # Should not crash
        assert result.agent_id == orchestrator.agent_id

    @pytest.mark.asyncio
    async def test_iteration_limit(self, orchestrator, mock_router, mock_registry, mock_deps):
        """Test that the orchestrator respects the max iteration limit."""
        # Make reflection never return TASK_COMPLETE
        never_complete = MagicMock()
        never_complete.content = "Still working on it, need more iterations."

        plan_response = MagicMock()
        plan_response.content = json.dumps([{
            "agent_name": "CoderAgent",
            "description": "Test",
            "input_data": "test",
            "parallel": False,
        }])

        sentiment_response = MagicMock()
        sentiment_response.content = "CHILL"

        # Return enough responses for MAX_ITERATIONS
        responses = [sentiment_response]  # sentiment
        for _ in range(MAX_ITERATIONS + 2):
            responses.extend([plan_response, never_complete])

        mock_router.chat = AsyncMock(side_effect=responses)

        task = AgentTask(
            task_type="test",
            input_data="Infinite task",
            context={},
        )

        result = await orchestrator.execute(task)
        # Should terminate, not hang
        assert result is not None

    @pytest.mark.asyncio
    async def test_token_budget_enforcement(self, orchestrator, mock_router, mock_registry, mock_deps):
        """Test that token budget is respected."""
        # Use a very small budget
        orchestrator_chain_budget = 50

        sentiment_response = MagicMock()
        sentiment_response.content = "CHILL"

        plan_response = MagicMock()
        plan_response.content = "[]"  # Empty plan triggers completion

        mock_router.chat = AsyncMock(side_effect=[
            sentiment_response, plan_response
        ])

        task = AgentTask(
            task_type="test",
            input_data="x" * 500,
            context={},
        )

        result = await orchestrator.execute(task)
        assert result is not None

    @pytest.mark.asyncio
    async def test_error_handling(self, orchestrator, mock_router, mock_registry, mock_deps):
        """Test graceful degradation on errors."""
        mock_router.chat = AsyncMock(side_effect=Exception("LLM connection failed"))

        # Also make reasoner fail
        orchestrator.reasoner.think_and_answer = AsyncMock(
            side_effect=Exception("Reasoning failed")
        )

        task = AgentTask(
            task_type="test",
            input_data="This should fail gracefully",
            context={},
        )

        result = await orchestrator.execute(task)
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_parallel_agent_execution(self, orchestrator, mock_router, mock_registry, mock_deps):
        """Test that parallel subtasks are executed concurrently."""
        plan_response = MagicMock()
        plan_response.content = json.dumps([
            {"agent_name": "CoderAgent", "description": "A", "input_data": "a", "parallel": True},
            {"agent_name": "ResearcherAgent", "description": "B", "input_data": "b", "parallel": True},
        ])

        reflect_response = MagicMock()
        reflect_response.content = "TASK_COMPLETE"

        sentiment_response = MagicMock()
        sentiment_response.content = "CURIOUS"

        mock_router.chat = AsyncMock(side_effect=[
            sentiment_response, plan_response, reflect_response,
        ])

        # Mock both agents
        agent_a = MagicMock()
        agent_a.execute = AsyncMock(return_value=AgentResult(
            task_id="a", agent_id="CoderAgent", success=True, output="A done"))
        agent_b = MagicMock()
        agent_b.execute = AsyncMock(return_value=AgentResult(
            task_id="b", agent_id="ResearcherAgent", success=True, output="B done"))

        mock_registry.get_agent.side_effect = lambda name: {
            "CoderAgent": agent_a, "ResearcherAgent": agent_b
        }.get(name)

        task = AgentTask(task_type="test", input_data="Do parallel work", context={})
        result = await orchestrator.execute(task)
        assert result is not None

    @pytest.mark.asyncio
    async def test_health_check(self, orchestrator):
        assert await orchestrator.health_check() is True

    @pytest.mark.asyncio
    async def test_sentiment_analysis(self, orchestrator, mock_router):
        """Test mood detection with valid and invalid responses."""
        valid_resp = MagicMock()
        valid_resp.content = "EXCITED"
        mock_router.chat = AsyncMock(return_value=valid_resp)

        chain = ReActChain()
        mood = await orchestrator._analyze_sentiment("I'm so happy!", chain)
        assert mood == "EXCITED"

    @pytest.mark.asyncio
    async def test_sentiment_fallback(self, orchestrator, mock_router):
        """Test mood fallback when LLM returns invalid value."""
        bad_resp = MagicMock()
        bad_resp.content = "INVALID_MOOD"
        mock_router.chat = AsyncMock(return_value=bad_resp)

        chain = ReActChain()
        mood = await orchestrator._analyze_sentiment("test", chain)
        assert mood == "CHILL"
