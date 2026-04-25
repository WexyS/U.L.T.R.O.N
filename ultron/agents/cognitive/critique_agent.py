"""Critique Agent — Quality control for agent outputs."""

import logging
import json
import re
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.cognitive.critique")

class CritiqueAgent(BaseAgent):
    agent_name = "CritiqueAgent"
    agent_description = "Specialized Genesis agent for Critique tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="CritiqueAgent",
            agent_description="Performs quality control on agent outputs using predefined criteria.",
            capabilities=["quality_control", "critique"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        output_to_critique = task.input_data

        try:
            prompt = [
                {"role": "system", "content": "You are a quality control expert. Evaluate the output based on: accuracy, completeness, security, efficiency, and alignment. Rate each 0-10. Return JSON: {\"scores\": {\"accuracy\": 10, ...}, \"overall\": float, \"feedback\": \"...\"}"},
                {"role": "user", "content": f"Output: {output_to_critique}"}
            ]
            resp = await router.chat(prompt)
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                critique = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=critique
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Critique failed.")
        except Exception as e:
            logger.error(f"Critique failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
