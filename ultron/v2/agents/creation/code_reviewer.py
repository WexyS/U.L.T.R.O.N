"""Code Review Agent — Evaluating code quality and security."""

import logging
import json
import re
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.creation.reviewer")

class CodeReviewAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="CodeReviewAgent",
            agent_description="Performs deep code reviews for correctness, security, performance, and readability.",
            capabilities=["code_review", "static_analysis", "security_audit"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        code_to_review = task.input_data
        language = task.context.get("language", "python")

        try:
            prompt = [
                {"role": "system", "content": f"You are a senior {language} developer. Review the code based on Correctness, Security, Performance, Readability, and Maintainability. Rate each 0-10. Provide specific improvement suggestions. Return JSON: {{\"scores\": {{\"correctness\": 8, ...}}, \"overall\": float, \"suggestions\": [\"...\"], \"security_warnings\": [\"...\"]}}"},
                {"role": "user", "content": f"Code:\n{code_to_review}"}
            ]
            resp = await router.chat(prompt)
            
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                review_report = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=review_report
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Could not parse review report.")
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
