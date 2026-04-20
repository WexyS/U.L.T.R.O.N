"""Core types and data structures for the Ultron v2 system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    CODER = "coder"
    RESEARCHER = "researcher"
    RPA_OPERATOR = "rpa_operator"
    HOME_CONTROLLER = "home_controller"
    MEMORY_KEEPER = "memory_keeper"
    VOICE_ASSISTANT = "voice_assistant"
    # ── Yeni Agentlar ─────────────────────────────────────
    EMAIL = "email"
    SYSMON = "sysmon"
    CLIPBOARD = "clipboard"
    MEETING = "meeting"
    FILES = "files"
    CALENDAR = "calendar"
    TASK_MANAGER = "task_manager"
    ERROR_ANALYZER = "error_analyzer"
    VISION = "openguider_bridge"
    DEBATE = "debate"
    CLONER = "cloner"
    WHATSAPP = "whatsapp"
    ARCHITECT = "architect"
    GAMING = "gaming"


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class ToolCall:
    """Represents a tool/function call and its result."""
    name: str
    arguments: dict[str, Any]
    result: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    status: TaskStatus
    output: str = ""
    error: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Task:
    """A unit of work to be executed by an agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    description: str = ""
    intent: str = ""
    assigned_agent: Optional[AgentRole] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0  # Higher = more urgent
    max_retries: int = 3
    retry_count: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    result: Optional[TaskResult] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def should_retry(self) -> bool:
        return (
            self.status == TaskStatus.FAILED
            and self.retry_count < self.max_retries
        )

    def mark_running(self) -> None:
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()

    def mark_success(self, output: str = "", metadata: Optional[dict] = None) -> None:
        self.status = TaskStatus.SUCCESS
        self.completed_at = datetime.now()
        self.result = TaskResult(
            task_id=self.id,
            status=TaskStatus.SUCCESS,
            output=output,
            metadata=metadata or {},
        )

    def mark_failed(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.retry_count += 1
        self.result = TaskResult(
            task_id=self.id,
            status=TaskStatus.RETRYING if self.should_retry() else TaskStatus.FAILED,
            error=error,
        )
        if self.should_retry():
            self.status = TaskStatus.RETRYING


@dataclass
class AgentState:
    """Current state of an agent."""
    role: AgentRole
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_active: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
