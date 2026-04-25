import os
import logging
from typing import Optional, Any
from datetime import datetime

from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult
from ultron.v2.core.llm_router import router as default_router

logger = logging.getLogger(__name__)

class DocumentAgent(BaseAgent):
    """
    Corporate Documentation Agent.
    Converts raw ideas/code/text into professional Proposal formats 
    (LaTeX/Markdown) suitable for grants, festivals (e.g. Sosyalfest), or enterprise.
    """

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="DocumentAgent",
            agent_description="Corporate documentation node for proposals and LaTeX formatting.",
            capabilities=["documentation", "latex", "proposal_writing"],
            memory=memory,
            skill_engine=skill_engine
        )
        self.router = default_router

    def _default_system_prompt(self) -> str:
        return """You are the Ultron Corporate Documentation & Proposal Pipeline Node.
Your purpose is to take raw ideas, code, or unstructured text and format it into a professional, enterprise-grade project proposal.

You must structure your output using standard academic/corporate proposal frameworks.
Typical structure for a proposal:
1. Executive Summary (Özet)
2. Project Purpose and Scope (Amaç ve Kapsam)
3. Innovative Aspects / Unique Value Proposition (Yenilikçi Yön)
4. Methodology (Yöntem)
5. Expected Outcomes and Impact (Beklenen Sonuçlar ve Etki)
6. Feasibility & Timeline (Uygulanabilirlik ve Takvim)

If the user asks for LaTeX, you must output raw valid LaTeX code inside a ```latex code block.
If the user asks for Markdown, output a highly structured Markdown file.

Maintain an extremely professional, persuasive, and visionary tone. Avoid fluff, focus on concrete value and technical feasibility.
"""

    async def execute(self, task: AgentTask) -> AgentResult:
        logger.info(f"Document Agent executing task: {task.input_data}")
        start_time = datetime.now()
        
        messages = [
            {"role": "system", "content": self._default_system_prompt()},
            {"role": "user", "content": str(task.input_data)}
        ]

        # Use a higher temperature for creative proposal writing
        response = await self.router.chat(messages, temperature=0.7)

        latency = (datetime.now() - start_time).total_seconds() * 1000

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            output=response.content,
            latency_ms=latency
        )

    async def health_check(self) -> bool:
        return True
