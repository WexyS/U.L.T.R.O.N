"""Debate Agent - Wraps the DebateEngine for orchestrator use."""
from ultron.agents.base import Agent
from ultron.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus
from ultron.core.event_bus import EventBus
from ultron.core.blackboard import Blackboard
from ultron.core.llm_router import LLMRouter
from ultron.core.debate_engine import DebateEngine

import logging
logger = logging.getLogger(__name__)

class DebateAgent(Agent):
    agent_name = "DebateAgent"
    agent_description = "Specialized Genesis agent for Debate tasks."

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
            await self._publish_event("debate_result", {"task_id": task.task_id, "output": result.output, "error": result.error})
            
        self.event_bus.subscribe("debate_request", on_debate_request)

    async def execute(self, task: Task) -> TaskResult:
        self.state.status = AgentStatus.BUSY
        try:
            topic = task.input_data
            rounds = task.context.get("rounds", 2)
            
            logger.info(f"Starting Multi-Agent Debate on: {topic[:50]}...")
            lesson_context = task.context.get("lesson_context", "")
            result_dict = await self.debate_engine.run_debate(topic=topic, rounds=rounds, lesson_context=lesson_context)
            
            return TaskResult(
                task_id=task.task_id, 
                status=TaskStatus.SUCCESS, 
                output=result_dict["final_answer"], 
                metadata={"transcript": result_dict["transcript"]}
            )
        except Exception as e:
            return TaskResult(task_id=task.task_id, status=TaskStatus.FAILED, error=str(e))
        finally:
            self.state.status = AgentStatus.IDLE
