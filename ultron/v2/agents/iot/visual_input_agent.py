"""Visual Input Agent — Monitoring screen and camera for visual triggers."""

import logging
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus

logger = logging.getLogger("ultron.agents.iot.visual")

class VisualInputAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="VisualInput",
            agent_description="Monitors visual streams (screen/camera) to detect changes, objects, or UI elements.",
            capabilities=["visual_monitoring", "screen_analysis", "face_detection"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        
        try:
            # 1. Capture screen
            path = await self.request_skill("skill_screenshot")
            
            # 2. Analyze (can call ImageAnalysisAgent)
            # For now, just confirm capture
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={"screenshot_path": path, "message": "Visual input captured and ready for analysis."}
            )
        except Exception as e:
            logger.error(f"Visual input failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
