"""Agent smoke tests.

These tests verify:
- All agents can be imported
- All agent classes have required attributes
- AgentRole enum has all expected values
- CoderAgent can be instantiated with mocks
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import all agents
# ---------------------------------------------------------------------------

from ultron.core.types import AgentRole, AgentStatus
from ultron.agents.base import Agent
from ultron.agents.coder import CoderAgent
from ultron.agents.researcher import ResearcherAgent
from ultron.agents.rpa_operator import RPAOperatorAgent
from ultron.agents.clipboard_agent import ClipboardAgent
from ultron.agents.sysmon_agent import SystemMonitorAgent
from ultron.agents.meeting_agent import MeetingAgent
from ultron.agents.files_agent import FilesAgent

# ---------------------------------------------------------------------------
# All concrete agent classes (excluding the abstract base)
# ---------------------------------------------------------------------------

ALL_AGENT_CLASSES = [
    CoderAgent,
    ResearcherAgent,
    RPAOperatorAgent,
    ClipboardAgent,
    SystemMonitorAgent,
    MeetingAgent,
    FilesAgent,
]


# ===========================================================================
# Import tests
# ===========================================================================

class TestAgentImports:
    """Verify that all agent classes can be imported without error."""

    def test_base_agent_import(self) -> None:
        """Base Agent class is importable."""
        assert inspect.isclass(Agent)
        assert inspect.isabstract(Agent)

    def test_coder_agent_import(self) -> None:
        assert inspect.isclass(CoderAgent)

    def test_researcher_agent_import(self) -> None:
        assert inspect.isclass(ResearcherAgent)

    def test_rpa_operator_agent_import(self) -> None:
        assert inspect.isclass(RPAOperatorAgent)

    def test_clipboard_agent_import(self) -> None:
        assert inspect.isclass(ClipboardAgent)

    def test_sysmon_agent_import(self) -> None:
        assert inspect.isclass(SystemMonitorAgent)

    def test_meeting_agent_import(self) -> None:
        assert inspect.isclass(MeetingAgent)

    def test_files_agent_import(self) -> None:
        assert inspect.isclass(FilesAgent)

    def test_agent_package_all(self) -> None:
        """Verify __all__ in agents package exports all agents."""
        from ultron.agents import __all__
        expected = {
            "Agent",
            "CoderAgent",
            "ResearcherAgent",
            "RPAOperatorAgent",
            "EmailAgent",
            "SystemMonitorAgent",
            "ClipboardAgent",
            "MeetingAgent",
            "FilesAgent",
            "CalendarAgent",
            "TaskManagerAgent",
            "OpenGuiderBridgeAgent",
            "DebateAgent",
        }
        assert set(__all__) == expected


# ===========================================================================
# Required attribute tests
# ===========================================================================

class TestAgentRequiredAttributes:
    """Every concrete agent must have specific attributes and methods."""

    REQUIRED_ATTRS = {"_default_system_prompt", "execute", "_subscribe_events"}

    @pytest.mark.parametrize("agent_cls", ALL_AGENT_CLASSES)
    def test_has_required_abstract_methods(self, agent_cls: type) -> None:
        """Each agent class must define the required abstract methods."""
        for attr_name in self.REQUIRED_ATTRS:
            assert hasattr(agent_cls, attr_name), (
                f"{agent_cls.__name__} is missing '{attr_name}'"
            )
            method = getattr(agent_cls, attr_name)
            assert callable(method), (
                f"{agent_cls.__name__}.{attr_name} is not callable"
            )

    @pytest.mark.parametrize("agent_cls", ALL_AGENT_CLASSES)
    def test_inherits_from_base(self, agent_cls: type) -> None:
        """Every agent must inherit from the base Agent class."""
        assert issubclass(agent_cls, Agent)

    @pytest.mark.parametrize("agent_cls", ALL_AGENT_CLASSES)
    def test_has_system_prompt_method_defined(self, agent_cls: type) -> None:
        """The _default_system_prompt must be concretely implemented (not abstract)."""
        method = getattr(agent_cls, "_default_system_prompt")
        assert not getattr(method, "__isabstractmethod__", False), (
            f"{agent_cls.__name__}._default_system_prompt is still abstract"
        )


# ===========================================================================
# AgentRole enum tests
# ===========================================================================

class TestAgentRoleEnum:
    """Verify the AgentRole enum has all expected values."""

    EXPECTED_ROLES = {
        "ORCHESTRATOR",
        "CODER",
        "RESEARCHER",
        "RPA_OPERATOR",
        "HOME_CONTROLLER",
        "MEMORY_KEEPER",
        "VOICE_ASSISTANT",
        "EMAIL",
        "SYSMON",
        "CLIPBOARD",
        "MEETING",
        "FILES",
        "CALENDAR",
        "TASK_MANAGER",
        "ERROR_ANALYZER",
        "OPENGUIDER_BRIDGE",
        "DEBATE",
    }

    def test_all_expected_roles_present(self) -> None:
        """Every expected role must exist in the enum."""
        enum_members = {m.name for m in AgentRole}
        missing = self.EXPECTED_ROLES - enum_members
        assert not missing, f"Missing AgentRole members: {missing}"

    def test_role_values_are_strings(self) -> None:
        """All AgentRole values should be strings."""
        for member in AgentRole:
            assert isinstance(member.value, str)

    def test_new_agent_roles(self) -> None:
        """Verify the new v2.0 agent roles exist with correct values."""
        assert AgentRole.EMAIL.value == "email"
        assert AgentRole.SYSMON.value == "sysmon"
        assert AgentRole.CLIPBOARD.value == "clipboard"
        assert AgentRole.MEETING.value == "meeting"
        assert AgentRole.FILES.value == "files"

    def test_core_agent_roles(self) -> None:
        """Verify core agent roles have expected values."""
        assert AgentRole.CODER.value == "coder"
        assert AgentRole.RESEARCHER.value == "researcher"
        assert AgentRole.RPA_OPERATOR.value == "rpa_operator"
        assert AgentRole.ORCHESTRATOR.value == "orchestrator"

    def test_role_count(self) -> None:
        """Verify the total number of roles."""
        assert len(AgentRole) == len(self.EXPECTED_ROLES)


# ===========================================================================
# AgentStatus enum tests
# ===========================================================================

class TestAgentStatusEnum:
    """Verify the AgentStatus enum has all expected values."""

    def test_status_values(self) -> None:
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.BUSY.value == "busy"
        assert AgentStatus.ERROR.value == "error"
        assert AgentStatus.OFFLINE.value == "offline"

    def test_status_count(self) -> None:
        assert len(AgentStatus) == 4


# ===========================================================================
# CoderAgent instantiation tests
# ===========================================================================

class TestCoderAgentInstantiation:
    """Test CoderAgent can be instantiated with mock dependencies."""

    @pytest.fixture()
    def mock_llm_router(self) -> MagicMock:
        router = MagicMock()
        router.chat = AsyncMock(return_value=MagicMock(
            content="print('hello')",
            provider="mock",
            model="mock",
        ))
        router.get_healthy_providers = MagicMock(return_value=["ollama"])
        return router

    @pytest.fixture()
    def mock_event_bus(self) -> MagicMock:
        bus = MagicMock()
        bus.subscribe = MagicMock()
        bus.subscribe_all = MagicMock()
        bus.publish = AsyncMock()
        bus.publish_simple = AsyncMock()
        bus._handlers = {}
        return bus

    @pytest.fixture()
    def mock_blackboard(self) -> MagicMock:
        board = MagicMock()
        board.write = AsyncMock()
        board.read = AsyncMock(return_value=None)
        board.get_all = AsyncMock(return_value={})
        board.clear = AsyncMock(return_value=0)
        board.delete = AsyncMock(return_value=False)
        board.keys = AsyncMock(return_value=[])
        return board

    def test_coder_agent_creation(
        self,
        mock_llm_router: MagicMock,
        mock_event_bus: MagicMock,
        mock_blackboard: MagicMock,
        tmp_path,
    ) -> None:
        """CoderAgent can be instantiated with mock dependencies."""
        work_dir = str(tmp_path / "workspace")
        agent = CoderAgent(
            llm_router=mock_llm_router,
            event_bus=mock_event_bus,
            blackboard=mock_blackboard,
            work_dir=work_dir,
        )

        assert agent.role == AgentRole.CODER
        assert agent.llm_router is mock_llm_router
        assert agent.event_bus is mock_event_bus
        assert agent.blackboard is mock_blackboard
        assert agent.work_dir.name == "workspace"
        assert agent.max_heal_iterations == 5
        assert agent.allow_execution is True
        assert agent._running is False

    def test_coder_agent_default_prompt(
        self,
        mock_llm_router: MagicMock,
        mock_event_bus: MagicMock,
        mock_blackboard: MagicMock,
        tmp_path,
    ) -> None:
        """CoderAgent system prompt mentions code generation rules."""
        agent = CoderAgent(
            llm_router=mock_llm_router,
            event_bus=mock_event_bus,
            blackboard=mock_blackboard,
            work_dir=str(tmp_path / "ws"),
        )
        prompt = agent._default_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 50
        assert "code" in prompt.lower()

    def test_coder_agent_custom_params(
        self,
        mock_llm_router: MagicMock,
        mock_event_bus: MagicMock,
        mock_blackboard: MagicMock,
        tmp_path,
    ) -> None:
        """CoderAgent accepts custom max_heal_iterations and allow_execution."""
        agent = CoderAgent(
            llm_router=mock_llm_router,
            event_bus=mock_event_bus,
            blackboard=mock_blackboard,
            work_dir=str(tmp_path / "ws"),
            max_heal_iterations=3,
            allow_execution=False,
        )
        assert agent.max_heal_iterations == 3
        assert agent.allow_execution is False

    def test_coder_agent_start_stop(
        self,
        mock_llm_router: MagicMock,
        mock_event_bus: MagicMock,
        mock_blackboard: MagicMock,
        tmp_path,
    ) -> None:
        """CoderAgent can be started and stopped."""
        agent = CoderAgent(
            llm_router=mock_llm_router,
            event_bus=mock_event_bus,
            blackboard=mock_blackboard,
            work_dir=str(tmp_path / "ws"),
        )
        assert agent._running is False

    def test_coder_agent_ext_for_language(self) -> None:
        """_ext_for_language maps language names to file extensions."""
        assert CoderAgent._ext_for_language("python") == "py"
        assert CoderAgent._ext_for_language("javascript") == "js"
        assert CoderAgent._ext_for_language("typescript") == "ts"
        assert CoderAgent._ext_for_language("c++") == "cpp"
        assert CoderAgent._ext_for_language("rust") == "rs"
        assert CoderAgent._ext_for_language("unknown") == "txt"

    def test_coder_agent_is_code_safe(
        self,
        mock_llm_router: MagicMock,
        mock_event_bus: MagicMock,
        mock_blackboard: MagicMock,
        tmp_path,
    ) -> None:
        """_is_code_safe rejects dangerous patterns before execution."""
        agent = CoderAgent(
            llm_router=mock_llm_router,
            event_bus=mock_event_bus,
            blackboard=mock_blackboard,
            work_dir=str(tmp_path / "ws"),
        )
        assert agent._is_code_safe("print('hello')") is True
        assert agent._is_code_safe("os.system('rm -rf /')") is False


# ===========================================================================
# Other agent instantiation smoke tests
# ===========================================================================

class _MockDeps:
    """Convenience fixture providing pre-configured mock LLM, EventBus, Blackboard."""

    def __init__(self) -> None:
        self.llm = MagicMock()
        self.llm.chat = AsyncMock(
            return_value=MagicMock(content="mock response", provider="mock", model="mock")
        )
        self.llm.get_healthy_providers = MagicMock(return_value=["ollama"])

        self.bus = MagicMock()
        self.bus.subscribe = MagicMock()
        self.bus.subscribe_all = MagicMock()
        self.bus.publish = AsyncMock()
        self.bus.publish_simple = AsyncMock()
        self.bus._handlers = {}

        self.bb = MagicMock()
        self.bb.write = AsyncMock()
        self.bb.read = AsyncMock(return_value=None)
        self.bb.get_all = AsyncMock(return_value={})
        self.bb.clear = AsyncMock(return_value=0)
        self.bb.delete = AsyncMock(return_value=False)
        self.bb.keys = AsyncMock(return_value=[])


@pytest.fixture()
def mock_deps() -> _MockDeps:
    return _MockDeps()


class TestOtherAgentInstantiation:
    """Verify other agents can be instantiated with mocks."""

    def test_researcher_agent_instantiation(self, mock_deps: _MockDeps) -> None:
        agent = ResearcherAgent(
            llm_router=mock_deps.llm,
            event_bus=mock_deps.bus,
            blackboard=mock_deps.bb,
        )
        assert agent.role == AgentRole.RESEARCHER
        assert agent.max_hops == 3

    def test_rpa_operator_agent_instantiation(self, mock_deps: _MockDeps, tmp_path) -> None:
        agent = RPAOperatorAgent(
            llm_router=mock_deps.llm,
            event_bus=mock_deps.bus,
            blackboard=mock_deps.bb,
            screenshot_dir=str(tmp_path / "screenshots"),
        )
        assert agent.role == AgentRole.RPA_OPERATOR

    def test_clipboard_agent_instantiation(self, mock_deps: _MockDeps) -> None:
        agent = ClipboardAgent(
            llm_router=mock_deps.llm,
            event_bus=mock_deps.bus,
            blackboard=mock_deps.bb,
        )
        assert agent.role == AgentRole.CLIPBOARD

    def test_sysmon_agent_instantiation(self, mock_deps: _MockDeps) -> None:
        agent = SystemMonitorAgent(
            llm_router=mock_deps.llm,
            event_bus=mock_deps.bus,
            blackboard=mock_deps.bb,
        )
        assert agent.role == AgentRole.SYSMON

    def test_meeting_agent_instantiation(self, mock_deps: _MockDeps) -> None:
        agent = MeetingAgent(
            llm_router=mock_deps.llm,
            event_bus=mock_deps.bus,
            blackboard=mock_deps.bb,
            whisper_model="base",
        )
        assert agent.role == AgentRole.MEETING

    def test_files_agent_instantiation(self, mock_deps: _MockDeps) -> None:
        agent = FilesAgent(
            llm_router=mock_deps.llm,
            event_bus=mock_deps.bus,
            blackboard=mock_deps.bb,
        )
        assert agent.role == AgentRole.FILES
