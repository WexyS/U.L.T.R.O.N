"""Music Composition Agent — Designing melodies and musical structures."""

import logging
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.creative.music")

class MusicCompositionAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="MusicComposition",
            agent_description="Assists in composing music by suggesting melodies, chord progressions, and structural motifs.",
            capabilities=["music_theory", "composition", "melody_generation"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        genre = task.context.get("genre", "classical")
        mood = task.context.get("mood", "calm")

        try:
            prompt = [
                {"role": "system", "content": "You are a music composer. Suggest a chord progression and a melody motif for a piece in the given genre and mood. Use ABC notation or standard theory terms."},
                {"role": "user", "content": f"Genre: {genre}, Mood: {mood}"}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Music composition failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
