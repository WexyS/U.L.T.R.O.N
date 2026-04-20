"""Autonomous Research Agent — Self-directed deep dives into complex topics."""

import logging
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.meta.auto_research")

class AutonomousResearchAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="AutonomousResearcher",
            agent_description="Performs self-directed deep dives into complex topics, synthesizing information for the system's long-term memory.",
            capabilities=["autonomous_research", "information_synthesis", "trend_analysis"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        target_topic = task.input_data or "Latest advancements in Multi-Agent Systems"

        try:
            # 1. Search
            search_results = await self.request_skill("skill_web_search", query=target_topic, max_results=10)
            
            # 2. Synthesize for memory
            prompt = [
                {"role": "system", "content": "Synthesize this research into a structured report for the ULTRON Long-Term Memory. Focus on definitions, key players, and future trends."},
                {"role": "user", "content": f"Topic: {target_topic}\nResults: {search_results}"}
            ]
            resp = await router.chat(prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Autonomous research failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
