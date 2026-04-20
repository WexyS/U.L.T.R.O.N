"""Creative Problem Solving Agent — Using lateral thinking and diverse techniques."""

import logging
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.meta.cps")

class CreativeProblemSolvingAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="CreativeProblemSolver",
            agent_description="Applies lateral thinking, First Principles, and divergent thinking techniques to solve complex deadlocks.",
            capabilities=["lateral_thinking", "problem_solving", "brainstorming"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        problem = task.input_data

        try:
            prompt = [
                {"role": "system", "content": "You are a master of lateral thinking. Solve the provided problem using unconventional techniques (e.g., First Principles, Reverse Brainstorming). Provide 3 distinct solutions."},
                {"role": "user", "content": f"Problem: {problem}"}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Creative problem solving failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
