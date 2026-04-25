"""TaskManagerAgent — manages tasks, todos, and project tracking."""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Optional

from ultron.core.types import AgentRole, AgentState, AgentStatus, Task, TaskStatus, TaskResult
from ultron.core.event_bus import EventBus, Event
from ultron.core.blackboard import Blackboard
from ultron.core.llm_router import LLMRouter, LLMResponse
from ultron.agents.base import Agent

logger = logging.getLogger(__name__)


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskState(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskManagerAgent(Agent):
    agent_name = "TaskManagerAgent"
    agent_description = "Manages tasks, todos, and project tracking."

    """Manages tasks, todos, and project tracking.
    
    Capabilities:
    - Create, update, delete tasks
    - Prioritize and organize tasks
    - Track progress and completion
    - Generate task summaries and reports
    - Set deadlines and reminders
    """

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
    ) -> None:
        super().__init__(
            role=AgentRole.TASK_MANAGER,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
            system_prompt=self._default_system_prompt(),
        )
        self._tasks: list[dict] = []

    def _default_system_prompt(self) -> str:
        return """You are Ultron Task Manager Agent — a highly efficient task management assistant.
Your responsibilities:
1. Create, read, update, and delete tasks
2. Prioritize tasks (Low, Medium, High, Critical)
3. Track task progress and completion
4. Generate daily/weekly task summaries
5. Set deadlines and reminders
6. Organize tasks by project or category

Always respond in a clear, organized format. Use checkboxes, tables, or bullet points.
Prioritize tasks intelligently and suggest next actions."""

    async def execute(self, task: Task) -> TaskResult:
        """Execute a task management task."""
        self.state.status = AgentStatus.BUSY
        self.state.current_task = task

        try:
            messages = self._build_messages(task.input_data)
            response = await self._llm_chat(messages)

            # Parse and execute task management actions
            result = await self._process_task_action(task.input_data, response.content)

            self.state.status = AgentStatus.IDLE
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=result,
                agent=self.role.value,
            )
        except Exception as e:
            logger.error("TaskManagerAgent error: %s", e)
            self.state.status = AgentStatus.ERROR
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error=str(e),
                agent=self.role.value,
            )

    async def _process_task_action(self, user_input: str, llm_response: str) -> str:
        """Process task management actions."""
        lower = user_input.lower()

        # Create task
        if any(word in lower for word in ["add task", "create task", "new task", "todo"]):
            new_task = await self._create_task(user_input)
            if new_task:
                self._tasks.append(new_task)
                await self._publish_event("task_created", new_task)
                return f"✅ Task created:\n{self._format_task(new_task)}"

        # List tasks
        elif any(word in lower for word in ["list tasks", "show tasks", "my tasks", "what's pending"]):
            return self._list_tasks()

        # Complete task
        elif any(word in lower for word in ["complete", "done", "finish", "mark done"]):
            return await self._complete_task(user_input)

        # Delete task
        elif any(word in lower for word in ["delete", "remove", "cancel task"]):
            return self._delete_task(user_input)

        # Prioritize
        elif any(word in lower for word in ["prioritize", "priority", "urgent", "important"]):
            return self._prioritize_tasks(user_input)

        # Summary
        elif any(word in lower for word in ["summary", "report", "overview", "status"]):
            return self._generate_summary()

        # Default: use LLM response
        return llm_response

    async def _create_task(self, user_input: str) -> Optional[dict]:
        """Create a new task from natural language."""
        messages = self._build_messages(
            f"Extract task details from this request. Return: title, priority (low/medium/high/critical), "
            f"deadline (if mentioned), description, project/category.\n\nRequest: {user_input}"
        )
        response = await self._llm_chat(messages)

        now = datetime.now()
        return {
            "id": f"task_{len(self._tasks) + 1}",
            "title": user_input[:60],
            "description": user_input,
            "priority": Priority.MEDIUM.value,
            "status": TaskState.TODO.value,
            "created_at": now.isoformat(),
            "deadline": None,
            "project": "General",
            "completed_at": None,
        }

    def _list_tasks(self, filter_state: Optional[TaskState] = None) -> str:
        """List tasks with optional filter."""
        if not self._tasks:
            return "📋 No tasks yet. Add one!"

        tasks_to_show = (
            [t for t in self._tasks if t["status"] == filter_state.value]
            if filter_state
            else self._tasks
        )

        if not tasks_to_show:
            return f"📋 No {filter_state.value} tasks."

        # Group by status
        by_status = {}
        for t in tasks_to_show:
            by_status.setdefault(t["status"], []).append(t)

        lines = ["📋 **Task List:**\n"]
        for status, tasks in by_status.items():
            emoji = {"todo": "⏳", "in_progress": "🔄", "done": "✅", "cancelled": "❌"}.get(status, "•")
            lines.append(f"{emoji} **{status.upper()}**")
            for task in tasks:
                priority_icon = {"low": "🔵", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(task["priority"], "⚪")
                lines.append(f"  {priority_icon} {task['title']}")
            lines.append("")

        return "\n".join(lines)

    def _format_task(self, task: dict) -> str:
        """Format task for display."""
        return (
            f"• **{task['title']}**\n"
            f"  Priority: {task['priority'].upper()}\n"
            f"  Status: {task['status']}\n"
            f"  📝 {task.get('description', 'No description')}"
        )

    async def _complete_task(self, user_input: str) -> str:
        """Mark a task as complete."""
        # Simplified - complete last task
        for task in reversed(self._tasks):
            if task["status"] != TaskState.DONE.value:
                task["status"] = TaskState.DONE.value
                task["completed_at"] = datetime.now().isoformat()
                await self._publish_event("task_completed", task)
                return f"✅ Completed: {task['title']}"

        return "📋 No pending tasks to complete."

    def _delete_task(self, user_input: str) -> str:
        """Delete a task."""
        if not self._tasks:
            return "📋 No tasks to delete."
        
        # Simplified - delete last task
        deleted = self._tasks.pop()
        return f"🗑️ Deleted task: {deleted['title']}"

    def _prioritize_tasks(self, user_input: str) -> str:
        """Re-prioritize tasks based on input."""
        if not self._tasks:
            return "📋 No tasks to prioritize."
        
        # Mark high priority tasks
        for task in self._tasks:
            if any(word in user_input.lower() for word in ["urgent", "important", "critical"]):
                task["priority"] = Priority.HIGH.value
        
        return "🎯 Tasks reprioritized. High priority tasks:\n" + "\n".join(
            f"• 🔴 {t['title']}" for t in self._tasks if t["priority"] in [Priority.HIGH.value, Priority.CRITICAL.value]
        )

    def _generate_summary(self) -> str:
        """Generate task summary report."""
        if not self._tasks:
            return "📊 No tasks to summarize."

        total = len(self._tasks)
        by_status = {s.value: 0 for s in TaskState}
        for t in self._tasks:
            by_status[t["status"]] = by_status.get(t["status"], 0) + 1

        completion_rate = (by_status.get("done", 0) / total * 100) if total > 0 else 0

        return (
            f"📊 **Task Summary Report**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 Total Tasks: {total}\n"
            f"⏳ Todo: {by_status.get('todo', 0)}\n"
            f"🔄 In Progress: {by_status.get('in_progress', 0)}\n"
            f"✅ Done: {by_status.get('done', 0)}\n"
            f"❌ Cancelled: {by_status.get('cancelled', 0)}\n"
            f"📈 Completion Rate: {completion_rate:.1f}%\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )

    async def _subscribe_events(self) -> None:
        """Subscribe to task-related events."""
        await self.event_bus.subscribe("task_reminder", self._handle_reminder)
        await self.event_bus.subscribe("task_sync", self._handle_sync)

    async def _handle_reminder(self, event: Event) -> None:
        """Handle task reminder event."""
        logger.info("TaskManagerAgent: Reminder triggered")

    async def _handle_sync(self, event: Event) -> None:
        """Handle task sync event."""
        logger.info("TaskManagerAgent: Syncing task data")
