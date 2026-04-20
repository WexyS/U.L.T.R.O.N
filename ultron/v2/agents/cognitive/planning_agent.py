"""Planning Agent — Sequencing agent actions for a task."""

import logging
import json
import re
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.cognitive.planning")

class PlanningAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="PlanningAgent",
            agent_description="Plans the optimal sequence of agent actions for a given task.",
            capabilities=["planning", "optimization"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        available_agents = task.context.get("available_agents", [])

        try:
            prompt = [
                {"role": "system", "content": "You are a master planner. Create an execution plan using the available agents. Return JSON: {\"steps\": [{\"agent\": \"...\", \"action\": \"...\"}], \"estimated_time_ms\": 5000, \"total_cost_estimate\": 0.05}"},
                {"role": "user", "content": f"Task: {task.input_data}\nAvailable Agents: {available_agents}"}
            ]
            resp = await router.chat(prompt)
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                plan = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=plan
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Planning failed.")
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
