"""Game Master Agent — Running text-based RPGs and scenarios."""

import logging
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.creative.gamemaster")

class GameMasterAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="GameMaster",
            agent_description="Expert GM for text-based adventures, handling rules, combat, and world reactivity.",
            capabilities=["game_mastering", "rpg_logic", "scenario_generation"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        user_action = task.input_data
        state = task.context.get("game_state", "Starting a new adventure.")

        try:
            prompt = [
                {"role": "system", "content": "You are the Game Master. Describe the outcome of the player's action. Maintain consistency with the game world and state. Provide choices for the next move."},
                {"role": "user", "content": f"Game State: {state}\nPlayer Action: {user_action}"}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Game mastering failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
