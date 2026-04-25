"""Architect Agent — Designing systems and making architectural decisions."""

import logging
import json
import re
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.creation.architect")

class ArchitectAgent(BaseAgent):
    agent_name = "ArchitectAgent"
    agent_description = "Specialized Genesis agent for Architect tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="ArchitectAgent",
            agent_description="Expert system architect providing technical designs, technology choices, and scalability strategies.",
            capabilities=["system_design", "architecture", "tech_stack_selection"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        requirements = task.input_data

        try:
            prompt = [
                {"role": "system", "content": "You are a master system architect. Provide a high-level design based on the requirements. Include components, data flow (ASCII), technology suggestions, and security notes. Return JSON: {\"components\": [], \"data_flow\": \"...\", \"technologies\": {}, \"scalability\": \"...\", \"security\": \"...\"}"},
                {"role": "user", "content": f"Requirements: {requirements}"}
            ]
            resp = await router.chat(prompt)
            
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                design_report = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=design_report
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Could not parse architecture report.")
        except Exception as e:
            logger.error(f"System design failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
