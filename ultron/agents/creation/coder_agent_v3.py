"""Coder Agent v3.0 — Advanced autonomous coding with self-correction."""

import logging
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.creation.coder_v3")

class CoderAgentV3(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="CoderV3",
            agent_description="Advanced coding agent capable of building complex systems, debugging, and self-review.",
            capabilities=["coding", "refactoring", "architecting"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        instructions = task.input_data

        try:
            prompt = [
                {"role": "system", "content": "You are Ultron Coder v3.0. Write high-quality, production-ready code based on the instructions. Think step-by-step."},
                {"role": "user", "content": instructions}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Coding failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
