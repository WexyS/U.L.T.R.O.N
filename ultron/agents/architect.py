"""Agent Architect — Specialized agent for autonomous agent creation and library indexing."""
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from ultron.agents.base import Agent
from ultron.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus
from ultron.core.event_bus import EventBus
from ultron.core.blackboard import Blackboard
from ultron.core.llm_router import LLMRouter

logger = logging.getLogger(__name__)

class AgentArchitect(Agent):
    """The Architect designs and builds new specialized agents and tools."""
    
    def __init__(self, llm_router: LLMRouter, event_bus: EventBus, blackboard: Blackboard, knowledge_engine: Any):
        super().__init__(role=AgentRole.ARCHITECT, llm_router=llm_router, event_bus=event_bus, blackboard=blackboard)
        self.knowledge = knowledge_engine

    def _default_system_prompt(self) -> str:
        return (
            "You are the Ultron Agent Architect.\n"
            "Your mission is to design, code, and deploy new specialized AI agents and skills.\n"
            "You have access to a Local Knowledge Engine that contains documentation for various libraries.\n"
            "When asked to create an agent for a specific library:\n"
            "1. Search the local knowledge base for library details.\n"
            "2. Design an agent class that inherits from Agent.\n"
            "3. Implement the required logic, system prompts, and tool calls.\n"
            "4. Provide the complete source code for the new agent.\n"
            "Your designs must be modular, robust, and adhere to Ultron's v2 architecture."
        )

    async def _subscribe_events(self) -> None:
        """Subscribe to architectural events."""
        pass

    async def execute(self, task: Task) -> TaskResult:
        self.state.status = AgentStatus.BUSY
        try:
            # Check if dataset indexing is requested
            if "dataset" in task.input_data.lower() or "veri seti" in task.input_data.lower():
                path = task.context.get("path")
                if path:
                    await self.knowledge.index_dataset(path)
                    return TaskResult(task_id=task.task_id, status=TaskStatus.SUCCESS, output=f"Successfully indexed dataset at {path}. My context awareness is increasing.")

            # Check if directory indexing is requested
            if "index" in task.input_data.lower() or "indeksle" in task.input_data.lower():
                path = task.context.get("path")
                if path:
                    await self.knowledge.index_directory(path)
                    return TaskResult(task_id=task.task_id, status=TaskStatus.SUCCESS, output=f"Successfully indexed library at {path}")

            # General architectural task
            messages = self._build_messages(task.input_data)
            response = await self._llm_chat(messages)
            
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.SUCCESS,
                output=response.content
            )
        except Exception as e:
            return TaskResult(task_id=task.task_id, status=TaskStatus.FAILED, error=str(e))
        finally:
            self.state.status = AgentStatus.IDLE
