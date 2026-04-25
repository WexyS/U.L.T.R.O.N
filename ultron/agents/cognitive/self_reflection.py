"""Self-Reflection Agent — Critiquing and improving responses."""

import logging
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.cognitive.reflection")

class SelfReflectionAgent(BaseAgent):
    agent_name = "SelfReflectionAgent"
    agent_description = "Specialized Genesis agent for SelfReflection tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="SelfReflection",
            agent_description="Critiques its own or other agents' outputs to ensure accuracy and completeness.",
            capabilities=["reflection", "critique", "improvement"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        original_task = task.context.get("original_task", "")
        response_to_reflect = task.input_data

        try:
            prompt = [
                {"role": "system", "content": "You are a self-reflection expert. Evaluate the given response against the original task. Provide a score (0-1), identify issues, and suggest an improved version. Return as JSON: {\"score\": float, \"issues\": [], \"improved_response\": \"...\"}"},
                {"role": "user", "content": f"Original Task: {original_task}\nResponse: {response_to_reflect}"}
            ]
            resp = await router.chat(prompt)
            # Simplified parsing for the example
            import json, re
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                reflection = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=reflection
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Reflection failed.")
        except Exception as e:
            logger.error(f"Reflection failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
