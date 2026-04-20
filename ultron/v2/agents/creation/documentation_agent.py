"""Documentation Agent — Generating docstrings, READMEs, and API docs."""

import logging
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.creation.documentation")

class DocumentationAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="DocumentationAgent",
            agent_description="Specializes in writing high-quality documentation including docstrings, READMEs, and API guides.",
            capabilities=["documentation", "readme_generation", "api_documentation"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        content_to_doc = task.input_data
        doc_type = task.context.get("doc_type", "docstring") # docstring, readme, api
        language = task.context.get("language", "python")

        try:
            prompt = [
                {"role": "system", "content": f"You are a technical writer expert in {language}. Generate a {doc_type} for the provided content. Follow industry standards (e.g., Google-style for Python)."},
                {"role": "user", "content": f"Content:\n{content_to_doc}"}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Documentation failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
