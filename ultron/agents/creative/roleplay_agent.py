"""Roleplay Agent — Assuming diverse personas for interactive sessions."""

import logging
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.creative.roleplay")

class RoleplayAgent(BaseAgent):
    agent_name = "RoleplayAgent"
    agent_description = "Specialized Genesis agent for Roleplay tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="RoleplayAgent",
            agent_description="Expert in assuming diverse personas, maintaining consistent tone, knowledge, and behavior.",
            capabilities=["persona_simulation", "roleplay", "empathy"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        persona = task.context.get("persona", "A helpful Victorian scholar.")
        user_input = task.input_data

        try:
            prompt = [
                {"role": "system", "content": f"You are roleplaying as: {persona}. Maintain this character perfectly. Stay in world and respond based on your persona's knowledge and personality."},
                {"role": "user", "content": user_input}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Roleplay failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
