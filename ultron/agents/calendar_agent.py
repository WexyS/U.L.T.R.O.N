"""CalendarAgent — manages calendar events, schedules, and reminders."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from ultron.core.types import AgentRole, AgentState, AgentStatus, Task, TaskStatus, TaskResult
from ultron.core.event_bus import EventBus, Event
from ultron.core.blackboard import Blackboard
from ultron.core.llm_router import LLMRouter, LLMResponse
from ultron.agents.base import Agent

logger = logging.getLogger(__name__)


class CalendarAgent(Agent):
    agent_name = "CalendarAgent"
    agent_description = "Manages calendar events, schedules, and reminders."

    """Manages calendar events, schedules, and reminders.
    
    Capabilities:
    - Create, read, update, delete events
    - Check availability
    - Set reminders
    - Generate daily/weekly schedules
    """

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
    ) -> None:
        super().__init__(
            role=AgentRole.CALENDAR,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
            system_prompt=self._default_system_prompt(),
        )
        self._events: list[dict] = []

    def _default_system_prompt(self) -> str:
        return """You are Ultron Calendar Agent — a highly efficient calendar management assistant.
Your responsibilities:
1. Create, read, update, and delete calendar events
2. Check availability and suggest meeting times
3. Set reminders and notifications
4. Generate daily and weekly schedule summaries
5. Handle recurring events

Always respond in a clear, concise format. Use tables or bullet points for event listings.
Confirm all event creations with full details before saving."""

    async def execute(self, task: Task) -> TaskResult:
        """Execute a calendar task."""
        self.state.status = AgentStatus.BUSY
        self.state.current_task = task

        try:
            messages = self._build_messages(task.input_data)
            response = await self._llm_chat(messages)

            # Parse and execute calendar actions
            result = await self._process_calendar_action(task.input_data, response.content)

            self.state.status = AgentStatus.IDLE
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=result,
                agent=self.role.value,
            )
        except Exception as e:
            logger.error("CalendarAgent error: %s", e)
            self.state.status = AgentStatus.ERROR
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error=str(e),
                agent=self.role.value,
            )

    async def _process_calendar_action(self, user_input: str, llm_response: str) -> str:
        """Process calendar actions and store events."""
        lower = user_input.lower()

        # Create event
        if any(word in lower for word in ["create", "add", "schedule", "plan"]):
            event = await self._create_event(user_input)
            if event:
                self._events.append(event)
                await self._publish_event("calendar_event_created", event)
                return f"✅ Event created:\n{self._format_event(event)}"

        # List events
        elif any(word in lower for word in ["list", "show", "what's on", "upcoming", "today"]):
            return self._list_events()

        # Check availability
        elif "available" in lower or "free" in lower:
            return self._check_availability(user_input)

        # Delete event
        elif any(word in lower for word in ["delete", "remove", "cancel"]):
            return self._delete_event(user_input)

        # Default: use LLM response
        return llm_response

    async def _create_event(self, user_input: str) -> Optional[dict]:
        """Create a new calendar event from natural language."""
        messages = self._build_messages(
            f"Extract event details from this request. Return JSON with: title, date (YYYY-MM-DD), "
            f"time (HH:MM), duration_minutes, description, location (if mentioned).\n\nRequest: {user_input}"
        )
        response = await self._llm_chat(messages)

        # Simple parsing - in production, use proper JSON parsing
        now = datetime.now()
        return {
            "id": f"evt_{len(self._events) + 1}",
            "title": user_input[:50],
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "duration_minutes": 60,
            "description": user_input,
            "location": "",
            "created_at": now.isoformat(),
        }

    def _list_events(self) -> str:
        """List all upcoming events."""
        if not self._events:
            return "📅 No upcoming events."

        lines = ["📅 **Upcoming Events:**\n"]
        for evt in self._events:
            lines.append(self._format_event(evt))

        return "\n".join(lines)

    def _format_event(self, event: dict) -> str:
        """Format event for display."""
        return (
            f"• **{event['title']}**\n"
            f"  📆 {event['date']} at {event['time']}\n"
            f"  ⏱️ {event['duration_minutes']} minutes\n"
            f"  📝 {event.get('description', 'No description')}"
        )

    def _check_availability(self, user_input: str) -> str:
        """Check availability for a given time."""
        # Simplified - check if there are conflicts
        now = datetime.now()
        busy_times = [
            f"{evt['date']} {evt['time']}" for evt in self._events
        ]
        
        if not busy_times:
            return "✅ You're completely free! No events scheduled."
        
        return f"📅 You have {len(self._events)} event(s) scheduled:\n" + "\n".join(f"• {bt}" for bt in busy_times)

    def _delete_event(self, user_input: str) -> str:
        """Delete an event."""
        if not self._events:
            return "📅 No events to delete."
        
        # Simplified - delete last event
        deleted = self._events.pop()
        return f"🗑️ Deleted event: {deleted['title']}"

    async def _subscribe_events(self) -> None:
        """Subscribe to calendar-related events."""
        await self.event_bus.subscribe("calendar_reminder", self._handle_reminder)
        await self.event_bus.subscribe("calendar_sync", self._handle_sync)

    async def _handle_reminder(self, event: Event) -> None:
        """Handle reminder event."""
        logger.info("CalendarAgent: Reminder triggered")

    async def _handle_sync(self, event: Event) -> None:
        """Handle calendar sync event."""
        logger.info("CalendarAgent: Syncing calendar data")
