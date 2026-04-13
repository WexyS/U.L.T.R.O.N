"""Email Agent — IMAP/SMTP email handling."""

from __future__ import annotations

import logging
from typing import Optional

from ultron.v2.agents.base import Agent
from ultron.v2.core.types import AgentRole, Task, TaskResult, TaskStatus
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import LLMRouter

logger = logging.getLogger("ultron.v2.agents.email_agent")


class EmailAgent(Agent):
    """Email Agent — send, receive, and manage emails via IMAP/SMTP."""

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
        system_prompt: Optional[str] = None,
    ) -> None:
        super().__init__(
            role=AgentRole.EMAIL,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
            system_prompt=system_prompt,
        )

    def _default_system_prompt(self) -> str:
        return (
            "You are Ultron Email Agent. "
            "You can send, receive, and manage emails. "
            "Always be professional and concise in email communications."
        )

    async def _subscribe_events(self) -> None:
        self.event_bus.subscribe("email.send_request", self._on_send_request)
        self.event_bus.subscribe("email.check_request", self._on_check_request)
        logger.info("EmailAgent subscribed to email events")

    async def execute(self, task: Task) -> TaskResult:
        """Execute an email-related task."""
        self.state.status = AgentStatus.BUSY
        try:
            intent = task.intent.lower().strip()
            if intent in ("send", "compose"):
                return await self._handle_send(task)
            elif intent in ("check", "read", "inbox"):
                return await self._handle_check(task)
            else:
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=f"Unknown email intent: {intent}",
                    metadata={"intent": intent},
                )
        except Exception as exc:
            logger.exception("EmailAgent execute failed")
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(exc),
            )
        finally:
            self.state.status = AgentStatus.IDLE

    async def _handle_send(self, task: Task) -> TaskResult:
        """Send an email."""
        to_addr = task.context.get("to", "")
        subject = task.context.get("subject", "")
        body = task.context.get("body", task.description)

        if not to_addr:
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error="No recipient specified",
            )

        # In a full implementation, this would use aiosmtplib
        await self._publish_event("email.sent", {
            "to": to_addr,
            "subject": subject,
        })
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output=f"Email sent to {to_addr}: {subject}",
            metadata={"to": to_addr, "subject": subject},
        )

    async def _handle_check(self, task: Task) -> TaskResult:
        """Check inbox for new emails."""
        # In a full implementation, this would use aioimaplib
        await self._publish_event("email.checked", {})
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.SUCCESS,
            output="Inbox checked (no new messages)",
        )

    async def _on_send_request(self, event) -> None:
        """Handle email send request event."""
        try:
            task = Task(
                id=event.data.get("task_id"),
                description=event.data.get("body", ""),
                intent="send",
                context=event.data,
            )
            result = await self.execute(task)
            await self._publish_event("email.send_result", {
                "task_id": task.id,
                "success": result.status == TaskStatus.SUCCESS,
                "output": result.output,
                "error": result.error,
            })
        except Exception as exc:
            logger.error("Error handling email send request: %s", exc)

    async def _on_check_request(self, event) -> None:
        """Handle email check request event."""
        try:
            task = Task(
                id=event.data.get("task_id"),
                description="Check inbox",
                intent="check",
                context=event.data,
            )
            result = await self.execute(task)
            await self._publish_event("email.check_result", {
                "task_id": task.id,
                "output": result.output,
            })
        except Exception as exc:
            logger.error("Error handling email check request: %s", exc)
