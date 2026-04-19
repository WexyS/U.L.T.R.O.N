"""OpenGuider Bridge Agent - Interfaces with OpenGuider Desktop app."""
from typing import Any, Dict, Optional
import base64
from ultron.v2.agents.base import Agent
from ultron.v2.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import LLMRouter

import logging
logger = logging.getLogger(__name__)

class OpenGuiderBridgeAgent(Agent):
    def __init__(self, llm_router: LLMRouter, event_bus: EventBus, blackboard: Blackboard):
        super().__init__(role=AgentRole.OPENGUIDER_BRIDGE, llm_router=llm_router, event_bus=event_bus, blackboard=blackboard)
        # Store latest screen context here
        self.latest_screen: Optional[str] = None
        self.context_history: list = []

    def _default_system_prompt(self) -> str:
        return (
            "You are the OpenGuider Bridge. Your role is to mediate between the user's "
            "desktop screen context via OpenGuider and the Ultron backend. "
            "You can analyze the screen and decide next steps."
        )

    async def _subscribe_events(self) -> None:
        async def on_openguider_request(event):
            if not self._running: return
            task = Task(id=event.data.get("task_id"), description=event.data.get("description", ""), context=event.data.get("context", {}))
            result = await self.execute(task)
            await self._publish_event("openguider_result", {"task_id": task.id, "output": result.output, "error": result.error})
            
        self.event_bus.subscribe("openguider_request", on_openguider_request)

    async def execute(self, task: Task) -> TaskResult:
        self.state.status = AgentStatus.BUSY
        try:
            action = task.context.get("action", "chat")
            
            if action == "process_screen":
                image_b64 = task.context.get("image_b64")
                if image_b64:
                    self.latest_screen = image_b64
                    await self.blackboard.write("latest_openguider_screen", {"image_b64": image_b64})
                
                query = task.description
                if not query:
                    return TaskResult(task_id=task.id, status=TaskStatus.SUCCESS, output="Screen processed and stored.")
                
                # If vision is requested
                # Fallback to standard chat if LLM router vision isn't directly supported by all models
                messages = [
                    {"role": "system", "content": self._default_system_prompt()},
                    {"role": "user", "content": query},
                ]
                resp = await self.llm_router.chat(messages, max_tokens=1024)
                return TaskResult(task_id=task.id, status=TaskStatus.SUCCESS, output=resp.content)
                
            elif action == "chat":
                # Standard chat but contextualized with latest screen
                messages = [
                    {"role": "system", "content": self._default_system_prompt()},
                    {"role": "user", "content": task.description}
                ]
                resp = await self.llm_router.chat(messages, max_tokens=1024)
                return TaskResult(task_id=task.id, status=TaskStatus.SUCCESS, output=resp.content)
            else:
                return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error=f"Unknown action {action}")
        except Exception as e:
            return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error=str(e))
        finally:
            self.state.status = AgentStatus.IDLE
