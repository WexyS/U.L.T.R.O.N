"""Meta-Reasoning Agent — Strategy selection for problem solving."""

import logging
import json
import re
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.cognitive.meta_reasoning")

class MetaReasoningAgent(BaseAgent):
    agent_name = "MetaReasoningAgent"
    agent_description = "Specialized Genesis agent for MetaReasoning tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="MetaReasoning",
            agent_description="Selects the best problem-solving strategy based on the nature of the task.",
            capabilities=["strategy_selection", "reasoning"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        try:
            prompt = [
                {"role": "system", "content": "You are a meta-reasoning expert. Determine the best strategy for the given task. Options: direct_answer, research_then_answer, code_and_run, multi_step_plan, ask_clarification. Return JSON: {\"strategy\": \"...\", \"confidence\": float, \"rationale\": \"...\", \"suggested_agents\": []}"},
                {"role": "user", "content": f"Task: {task.input_data}"}
            ]
            resp = await router.chat(prompt)
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                strategy = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=strategy
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Strategy selection failed.")
        except Exception as e:
            logger.error(f"Meta-reasoning failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
