"""Summarization Agent — Distilling long content into key insights."""

import logging
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.communication.summarization")

class SummarizationAgent(BaseAgent):
    agent_name = "SummarizationAgent"
    agent_description = "Specialized Genesis agent for Summarization tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="SummarizationAgent",
            agent_description="Summarizes documents, URLs, and conversations into concise formats like bullet points or executive summaries.",
            capabilities=["summarization", "information_extraction", "tldr"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        content = task.input_data
        format_type = task.context.get("format", "bullet_points") # bullet_points, paragraph, tldr

        try:
            prompt = [
                {"role": "system", "content": f"You are an expert at summarization. Provide a {format_type} summary of the given content. Be concise and capture all key points."},
                {"role": "user", "content": f"Content:\n{content}"}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
