"""Self-Improvement Agent — Analyzing system performance and proposing optimizations."""

import logging
import json
import re
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.meta.self_improvement")

class SelfImprovementAgent(BaseAgent):
    agent_name = "SelfImprovementAgent"
    agent_description = "Specialized Genesis agent for SelfImprovement tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="SelfImprovement",
            agent_description="Analyzes system performance, logs, and user feedback to propose architectural and algorithmic improvements.",
            capabilities=["self_optimization", "architectural_review", "system_evolution"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        performance_data = task.input_data # Metrics, logs, feedback
        
        try:
            prompt = [
                {"role": "system", "content": "You are the ULTRON Self-Evolution Engine. Analyze the system data and propose specific improvements (code refactors, prompt adjustments, new tools). Return JSON: {\"target_component\": \"...\", \"problem\": \"...\", \"proposed_solution\": \"...\", \"priority\": 1-10}"},
                {"role": "user", "content": f"System Data:\n{performance_data}"}
            ]
            resp = await router.chat(prompt)
            
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                improvement_plan = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=improvement_plan
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Self-improvement analysis failed.")
        except Exception as e:
            logger.error(f"Self-improvement failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
