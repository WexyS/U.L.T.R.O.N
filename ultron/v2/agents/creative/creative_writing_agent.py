"""Creative Writing Agent — Writing poetry, scripts, and lyrics."""

import logging
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.creative.writing")

class CreativeWritingAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="CreativeWriting",
            agent_description="Expert in artistic writing forms including poetry, screenplays, and song lyrics.",
            capabilities=["poetry", "scriptwriting", "lyric_generation"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        format_type = task.context.get("format", "poem")
        prompt_text = task.input_data

        try:
            prompt = [
                {"role": "system", "content": f"You are a creative writer. Write a {format_type} about the given topic. Use rich metaphors and evocative language."},
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
            logger.error(f"Creative writing failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
