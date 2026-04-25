"""Learning Agent — Extracting lessons from task execution."""

import logging
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.cognitive.learning")

class LearningAgent(BaseAgent):
    agent_name = "LearningAgent"
    agent_description = "Specialized Genesis agent for Learning tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="LearningAgent",
            agent_description="Learns from successful and failed tasks to improve future performance.",
            capabilities=["learning", "optimization"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        task_info = task.context.get("task_info", {})
        result_info = task.input_data

        try:
            prompt = [
                {"role": "system", "content": "Analyze this task and its result. What was learned? If it failed, why? If it succeeded, what was the winning pattern? Provide a summary for long-term memory."},
                {"role": "user", "content": f"Task: {task_info}\nResult: {result_info}"}
            ]
            resp = await router.chat(prompt)
            # In Phase 8, we will store this in ProceduralMemory
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Learning failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
