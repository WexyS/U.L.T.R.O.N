from __future__ import annotations
import logging
from typing import Any, Optional

from ultron.core.types import AgentRole, Task, TaskResult, TaskStatus
from ultron.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class ResourceAgent(BaseAgent):
    agent_name = "ResourceAgent"
    agent_description = "Agent specialized in discovering and analyzing AI resources (models, datasets, tools)."

    """Agent specialized in discovering and analyzing AI resources (models, datasets, tools)."""

    def __init__(self, llm_router: Any, event_bus: Any, blackboard: Any):
        super().__init__(role=AgentRole.RESOURCER, llm_router=llm_router, event_bus=event_bus, blackboard=blackboard)

    def _default_system_prompt(self) -> str:
        return (
            "You are the Resource Discovery Specialist of Ultron. Your goal is to find "
            "the best AI models, datasets, and tools for the user."
        )

    async def _subscribe_events(self) -> None:
        # Standard subscription for tasks
        pass

    async def execute(self, task: Task) -> TaskResult:
        self.update_status(TaskStatus.RUNNING)
        logger.info("ResourceAgent executing: %s", task.input_data)

        # 1. Analyze request to see what kind of resource is needed
        analysis_prompt = [
            {"role": "system", "content": "You are the Resource Discovery Specialist of Ultron. Analyze the user request and identify what type of AI resource they are looking for (e.g., Free LLM, Dataset, Image Gen Tool, MCP Server)."},
            {"role": "user", "content": task.input_data}
        ]
        analysis = await self.llm_router.chat(analysis_prompt)
        resource_type = analysis.content

        # 2. Search for resources (simulated search + knowledge retrieval)
        # In a real scenario, this would use ResearcherAgent or direct search tools
        search_prompt = [
            {"role": "system", "content": "Search for the best free AI resources matching this requirement. Focus on high-quality, free, and accessible tools. Provide a list with links and brief descriptions."},
            {"role": "user", "content": f"Resource Type: {resource_type}\nRequirement: {task.input_data}"}
        ]
        results = await self.llm_router.chat(search_prompt)

        # 3. Final synthesis
        self.state.tasks_completed += 1
        self.update_status(TaskStatus.SUCCESS)
        return TaskResult(
            status=TaskStatus.SUCCESS,
            output=results.content,
            agent_role=self.role
        )
