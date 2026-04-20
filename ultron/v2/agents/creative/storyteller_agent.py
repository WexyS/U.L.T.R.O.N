"""Storyteller Agent — Creating immersive narratives and worlds."""

import logging
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.creative.storyteller")

class StorytellerAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="Storyteller",
            agent_description="Expert in narrative design, world-building, and character development.",
            capabilities=["storytelling", "world_building", "creative_writing"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        prompt_text = task.input_data
        genre = task.context.get("genre", "sci-fi")
        length = task.context.get("length", "medium")

        try:
            prompt = [
                {"role": "system", "content": f"You are a master storyteller. Create a {length} story in the {genre} genre based on the prompt. Focus on vivid imagery and character depth."},
                {"role": "user", "content": prompt_text}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Storytelling failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
