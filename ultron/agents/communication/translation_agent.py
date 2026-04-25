"""Translation Agent — High-quality multi-language translation."""

import logging
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.communication.translation")

class TranslationAgent(BaseAgent):
    agent_name = "TranslationAgent"
    agent_description = "Specialized Genesis agent for Translation tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="TranslationAgent",
            agent_description="Expert translator supporting 100+ languages with tone preservation.",
            capabilities=["translation", "language_detection", "localization"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        text = task.input_data
        target_lang = task.context.get("target_lang", "tr")
        preserve_tone = task.context.get("preserve_tone", True)

        try:
            tone_msg = "Preserve the original tone (formal/casual)." if preserve_tone else ""
            prompt = [
                {"role": "system", "content": f"You are a professional translator. Translate the text to {target_lang}. {tone_msg} Return ONLY the translated text."},
                {"role": "user", "content": text}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content.strip()
            )
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
