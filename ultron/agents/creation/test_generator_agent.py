"""Test Generator Agent — Generating unit and integration tests."""

import logging
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.creation.testgen")

class TestGeneratorAgent(BaseAgent):
    agent_name = "TestGeneratorAgent"
    agent_description = "Specialized Genesis agent for TestGenerator tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="TestGeneratorAgent",
            agent_description="Generates automated test suites for given code using frameworks like pytest or Jest.",
            capabilities=["test_generation", "unit_testing", "integration_testing"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        code_to_test = task.input_data
        language = task.context.get("language", "python")
        framework = "pytest" if language.lower() == "python" else "Jest"

        try:
            prompt = [
                {"role": "system", "content": f"You are a QA automation expert. Generate comprehensive {framework} tests for the given {language} code. Include happy path, edge cases, and error handling."},
                {"role": "user", "content": f"Code:\n{code_to_test}"}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
