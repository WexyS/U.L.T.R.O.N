"""Enhanced Researcher Agent — Multi-source web research with the new v3.0 infrastructure."""

import logging
import asyncio
from typing import List, Dict, Any
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.knowledge.researcher")

class EnhancedResearcherAgent(BaseAgent):
    agent_name = "EnhancedResearcherAgent"
    agent_description = "Specialized Genesis agent for EnhancedResearcher tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="EnhancedResearcher",
            agent_description="Multi-source web researcher utilizing Tavily, Serper, and DuckDuckGo.",
            capabilities=["web_search", "information_extraction", "synthesis"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        query = task.input_data
        
        try:
            # 1. Search across sources (using skill_engine)
            search_results = await self.request_skill("skill_web_search", query=query, max_results=8)
            
            # 2. Extract content from top URLs
            urls = [r["href"] for r in search_results[:3]]
            contents = []
            for url in urls:
                try:
                    content = await self.request_skill("skill_web_fetch", url=url)
                    contents.append({"url": url, "content": content[:2000]})
                except Exception as e:
                    logger.warning(f"Failed to fetch {url}: {e}")

            # 3. Synthesize findings
            synthesis_prompt = [
                {"role": "system", "content": "Synthesize the following research findings into a comprehensive report with citations."},
                {"role": "user", "content": f"Query: {query}\nFindings:\n{contents}"}
            ]
            resp = await router.chat(synthesis_prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content,
                tools_used=["skill_web_search", "skill_web_fetch"]
            )
        except Exception as e:
            logger.error(f"Research failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
