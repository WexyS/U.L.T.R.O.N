"""Writing Assistant Agent — Improving and generating text content."""

import logging
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.communication.writing")

class WritingAssistantAgent(BaseAgent):
    agent_name = "WritingAssistantAgent"
    agent_description = "Specialized Genesis agent for WritingAssistant tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="WritingAssistant",
            agent_description="Helps with writing, editing, and improving text content across different styles and tones.",
            capabilities=["content_writing", "editing", "grammar_check", "tone_adaptation"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        text = task.input_data
        goal = task.context.get("goal", "clarity") # clarity, formality, engagement, etc.

        try:
            prompt = [
                {"role": "system", "content": f"You are a professional writing assistant. Improve the text for better {goal}. Provide the improved version and a brief explanation of changes."},
                {"role": "user", "content": f"Text: {text}"}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Writing assistance failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
