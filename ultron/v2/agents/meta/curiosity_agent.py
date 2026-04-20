"""Curiosity Agent — Generating internal research tasks to expand the system's knowledge base."""

import logging
import json
import re
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.meta.curiosity")

class CuriosityAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="CuriosityAgent",
            agent_description="Generates autonomous internal queries to explore knowledge gaps and discover new tools or APIs.",
            capabilities=["autonomous_exploration", "knowledge_gap_identification", "curiosity"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        current_knowledge_summary = task.input_data or "General knowledge."

        try:
            prompt = [
                {"role": "system", "content": "You are the ULTRON Curiosity Engine. Identify a topic or technology that the system should learn about. Generate a specific research task. Return JSON: {\"topic\": \"...\", \"rationale\": \"...\", \"suggested_research_query\": \"...\"}"},
                {"role": "user", "content": f"Current Focus: {current_knowledge_summary}"}
            ]
            resp = await router.chat(prompt)
            
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                exploration_task = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=exploration_task
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Curiosity exploration failed.")
        except Exception as e:
            logger.error(f"Curiosity exploration failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
