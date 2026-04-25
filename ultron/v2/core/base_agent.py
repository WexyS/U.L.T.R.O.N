"""Base Agent Class for Ultron v3.0 AGI."""

import abc
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Dict
import uuid

class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    DISABLED = "disabled"

@dataclass
class AgentTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = "generic"
    input_data: Any = None
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1-10
    timeout_seconds: int = 300
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def id(self) -> str:
        """Alias for task_id to support legacy v2 agents."""
        return self.task_id

@dataclass
class AgentResult:
    task_id: str
    agent_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    tokens_used: int = 0
    latency_ms: float = 0.0
    tools_used: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

class BaseAgent(abc.ABC):
    """Abstract base class for all Ultron v3.0 agents."""

    def __init__(
        self,
        agent_name: str,
        agent_description: str,
        capabilities: List[str] = None,
        memory: Any = None,
        skill_engine: Any = None
    ):
        self.agent_id = str(uuid.uuid4())
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.capabilities = capabilities or []
        self.status = AgentStatus.IDLE
        self.memory = memory
        self.skill_engine = skill_engine
        self.logger = logging.getLogger(f"ultron.agents.{agent_name}")
        
    @property
    def name(self) -> str:
        """Alias for agent_name to maintain compatibility with registry."""
        return self.agent_name

    @abc.abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute the given task. Must be implemented by subclasses."""
        pass

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Perform a health check on the agent."""
        pass

    def get_capabilities(self) -> List[str]:
        """Return the list of capabilities of this agent."""
        return self.capabilities

    async def log_task(self, task: AgentTask, result: AgentResult):
        """Log the task and its result to the persistent storage."""
        # TODO: Implement SQLite logging for tasks
        self.logger.info(f"Task {task.task_id} completed by {self.agent_name}. Success: {result.success}")

    async def emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to the global event bus."""
        # This will be connected to the EventBus in later steps
        pass

    async def request_skill(self, skill_name: str, **kwargs) -> Any:
        """Request execution of a skill from the skill engine."""
        if not self.skill_engine:
            raise RuntimeError("Skill engine not initialized for this agent.")
        return await self.skill_engine.run(skill_name, **kwargs)

    async def consult_agent(self, agent_name: str, task: AgentTask) -> AgentResult:
        """Consult another agent for help with a subtask."""
        # This will be connected to the AgentRegistry in later steps
        pass

    def get_status(self) -> Dict[str, Any]:
        """Return the current status and metadata of the agent."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "capabilities": self.capabilities
        }
