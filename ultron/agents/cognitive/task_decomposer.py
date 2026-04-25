"""Task Decomposer Agent — Splitting complex tasks into atomic subtasks."""

import json
import re
import logging
from typing import List, Dict, Any
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.cognitive.decomposer")

class TaskDecomposerAgent(BaseAgent):
    agent_name = "TaskDecomposerAgent"
    agent_description = "Specialized Genesis agent for TaskDecomposer tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="TaskDecomposer",
            agent_description="Specialized agent for breaking down complex goals into a structured graph of subtasks.",
            capabilities=["decomposition", "task_planning"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        try:
            prompt = [
                {"role": "system", "content": "You are a decomposition expert. Break down the user's task into atomic subtasks. Return a JSON list: [{\"id\": 1, \"description\": \"...\", \"depends_on\": [], \"agent_capability\": \"...\", \"priority\": 5}]."},
                {"role": "user", "content": f"Task: {task.input_data}"}
            ]
            resp = await router.chat(prompt)
            
            # Parse JSON
            match = re.search(r"\[[\s\S]*\]", resp.content)
            if match:
                subtasks = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=subtasks
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Could not parse subtasks.")
        except Exception as e:
            logger.error(f"Decomposition failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
