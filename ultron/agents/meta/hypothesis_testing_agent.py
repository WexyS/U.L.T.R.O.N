"""Hypothesis Testing Agent — Designing and running experiments to validate ideas."""

import logging
import json
import re
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.meta.hypothesis")

class HypothesisTestingAgent(BaseAgent):
    agent_name = "HypothesisTestingAgent"
    agent_description = "Specialized Genesis agent for HypothesisTesting tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="HypothesisTesting",
            agent_description="Formulates and tests hypotheses about system behavior, code efficiency, or external facts.",
            capabilities=["experiment_design", "hypothesis_testing", "validation"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        problem_or_idea = task.input_data

        try:
            prompt = [
                {"role": "system", "content": "Formulate a testable hypothesis based on the idea. Design an experiment (steps) and criteria for success. Return JSON: {\"hypothesis\": \"...\", \"experiment_design\": [], \"success_criteria\": \"...\"}"},
                {"role": "user", "content": f"Idea: {problem_or_idea}"}
            ]
            resp = await router.chat(prompt)
            
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                design = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=design
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Hypothesis design failed.")
        except Exception as e:
            logger.error(f"Hypothesis design failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
