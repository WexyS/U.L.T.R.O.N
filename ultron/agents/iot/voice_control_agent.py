"""Voice Control Agent — Bridging natural language voice commands to system actions."""

import logging
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus

logger = logging.getLogger("ultron.agents.iot.voice")

class VoiceControlAgent(BaseAgent):
    agent_name = "VoiceControlAgent"
    agent_description = "Specialized Genesis agent for VoiceControl tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="VoiceControl",
            agent_description="Handles natural language voice commands, converting audio intent into executable actions.",
            capabilities=["voice_recognition", "intent_extraction", "text_to_speech"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        text_from_voice = task.input_data

        try:
            # 1. Intent Extraction (delegated to orchestrator or internal logic)
            # 2. Trigger TTS response if needed
            await self.request_skill("skill_notification_send", title="Voice Command", message=f"Processing: {text_from_voice}")
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=f"Voice command processed: {text_from_voice}"
            )
        except Exception as e:
            logger.error(f"Voice control failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
