"""Fact-Check Agent — Verifying claims across multiple sources."""

import logging
import json
import re
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.knowledge.factcheck")

class FactCheckAgent(BaseAgent):
    agent_name = "FactCheckAgent"
    agent_description = "Specialized Genesis agent for FactCheck tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="FactCheckAgent",
            agent_description="Verifies claims by cross-referencing multiple web sources and checking for contradictions.",
            capabilities=["fact_checking", "web_search", "verification"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        claim = task.input_data

        try:
            # 1. Search for the claim
            search_results = await self.request_skill("skill_web_search", query=f"fact check: {claim}", max_results=5)
            
            # 2. Analyze results
            prompt = [
                {"role": "system", "content": "Analyze the search results to verify the claim. Determine if it is true, false, or uncertain. Provide a confidence score and explanation. Return JSON: {\"verdict\": \"...\", \"confidence\": float, \"sources\": [], \"explanation\": \"...\"}"},
                {"role": "user", "content": f"Claim: {claim}\nResults: {search_results}"}
            ]
            resp = await router.chat(prompt)
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                result = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=result,
                    tools_used=["skill_web_search"]
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Fact check failed.")
        except Exception as e:
            logger.error(f"Fact check failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
