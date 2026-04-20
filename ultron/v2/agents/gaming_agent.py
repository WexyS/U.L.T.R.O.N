"""Gaming Agent — Challenger LoL & TFT Master."""

import logging
from typing import Optional

from ultron.v2.agents.base import Agent
from ultron.v2.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import LLMRouter

logger = logging.getLogger(__name__)


class GamingAgent(Agent):
    """A gaming assistant that acts as a Challenger LoL player and TFT Master."""

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
    ) -> None:
        super().__init__(
            role=AgentRole.GAMING,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
        )

    def _default_system_prompt(self) -> str:
        return (
            "You are an elite Gaming Assistant. You are a Challenger tier League of Legends player "
            "and a Master tier Teamfight Tactics (TFT) player. "
            "Your personality is confident, analytical, and sharp. You give advanced tactics, "
            "recommend team comps, explain patch changes, and offer deep macro and micro game knowledge.\n"
            "If the user asks about the current meta or TFT comps, you should use your internet search "
            "tool to fetch the most up-to-date information before responding.\n"
            "Format your responses clearly with bullet points, tier lists, or step-by-step guides."
        )

    async def _subscribe_events(self) -> None:
        async def on_gaming_request(event) -> None:
            if not self._running:
                return
            task = Task(
                id=event.data.get("task_id"),
                description=event.data.get("description", ""),
                context=event.data.get("context", {}),
            )
            result = await self.execute(task)
            await self._publish_event("gaming_result", {
                "task_id": task.id,
                "output": result.output,
                "error": result.error,
                "success": result.status == TaskStatus.SUCCESS,
            })

        self.event_bus.subscribe("gaming_request", on_gaming_request)

    async def execute(self, task: Task) -> TaskResult:
        """Execute a gaming task."""
        self.state.status = AgentStatus.BUSY
        self.state.current_task = task.id

        try:
            query = task.description

            # Check if it needs live data
            needs_search = any(word in query.lower() for word in ["meta", "tft", "comp", "yama", "patch", "tier", "build"])
            
            search_context = ""
            if needs_search:
                logger.info(f"GamingAgent searching web for: {query}")
                search_results = await self._search_duckduckgo(query + " tft comps lol meta 2026")
                if search_results:
                    search_context = "\n\nGüncel İnternet Verisi:\n" + "\n".join(
                        f"- {r.get('title')}: {r.get('body')}" for r in search_results[:5]
                    )

            messages = self._build_messages(
                f"Kullanıcının sorusu: {query}{search_context}"
            )

            response = await self._llm_chat(messages, max_tokens=2048, temperature=0.7)

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.SUCCESS,
                output=response.content,
            )
        except Exception as e:
            logger.error(f"GamingAgent Error: {e}")
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
            )
        finally:
            self.state.status = AgentStatus.IDLE
            self.state.current_task = None

    async def _search_duckduckgo(self, query: str) -> list[dict]:
        """Search using DuckDuckGo."""
        try:
            import asyncio
            from duckduckgo_search import DDGS

            def perform_search():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=5))

            urls = await asyncio.to_thread(perform_search)
            return urls
        except Exception as e:
            logger.warning("DuckDuckGo search failed for '%s': %s", query, e)
            return []
