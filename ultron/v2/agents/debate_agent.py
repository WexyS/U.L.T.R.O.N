"""Debate Agent - Wraps the DebateEngine for orchestrator use."""
from ultron.v2.agents.base import Agent
from ultron.v2.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus
from ultron.v2.core.event_bus import EventBus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import LLMRouter
from ultron.v2.core.debate_engine import DebateEngine

import logging
logger = logging.getLogger(__name__)

class DebateAgent(Agent):
    def __init__(self, llm_router: LLMRouter, event_bus: EventBus, blackboard: Blackboard):
        super().__init__(role=AgentRole.DEBATE, llm_router=llm_router, event_bus=event_bus, blackboard=blackboard)
        self.debate_engine = DebateEngine(llm_router)

    def _default_system_prompt(self) -> str:
        return ""

    async def _subscribe_events(self) -> None:
        async def on_debate_request(event):
            if not self._running: return
            task = Task(id=event.data.get("task_id"), description=event.data.get("description", ""), context=event.data.get("context", {}))
            result = await self.execute(task)
            await self._publish_event("debate_result", {"task_id": task.id, "output": result.output, "error": result.error})
            
        self.event_bus.subscribe("debate_request", on_debate_request)

    async def execute(self, task: Task) -> TaskResult:
        self.state.status = AgentStatus.BUSY
        try:
            topic = task.description
            rounds = task.context.get("rounds", 2)
            
            logger.info(f"Starting Multi-Agent Debate on: {topic[:50]}...")
            lesson_context = task.context.get("lesson_context", "")
            result_dict = await self.debate_engine.run_debate(topic=topic, rounds=rounds, lesson_context=lesson_context)
            
            return TaskResult(
                task_id=task.id, 
                status=TaskStatus.SUCCESS, 
                output=result_dict["final_answer"], 
                metadata={"transcript": result_dict["transcript"]}
            )
        except Exception as e:
            return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error=str(e))
        finally:
            self.state.status = AgentStatus.IDLE
