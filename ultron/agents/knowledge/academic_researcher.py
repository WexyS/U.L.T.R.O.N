"""Academic Research Agent — Specialized in searching scientific papers (ArXiv)."""

import logging
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.knowledge.academic")

class AcademicResearchAgent(BaseAgent):
    agent_name = "AcademicResearchAgent"
    agent_description = "Specialized Genesis agent for AcademicResearch tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="AcademicResearcher",
            agent_description="Expert in academic research, searching ArXiv and synthesizing papers.",
            capabilities=["academic_search", "paper_analysis"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        query = task.input_data

        try:
            # ArXiv API search
            arxiv_results = await self._search_arxiv(query)
            
            synthesis_prompt = [
                {"role": "system", "content": "Analyze the following academic paper summaries and provide a structured review in Turkish."},
                {"role": "user", "content": f"Topic: {query}\nPapers:\n{arxiv_results}"}
            ]
            resp = await router.chat(synthesis_prompt)
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=resp.content
            )
        except Exception as e:
            logger.error(f"Academic research failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def _search_arxiv(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            
            # Simple XML parsing
            root = ET.fromstring(resp.text)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            papers = []
            for entry in root.findall('atom:entry', ns):
                papers.append({
                    "title": entry.find('atom:title', ns).text.strip(),
                    "summary": entry.find('atom:summary', ns).text.strip(),
                    "url": entry.find('atom:id', ns).text
                })
            return papers

    async def health_check(self) -> bool:
        return True
