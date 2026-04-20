"""Document Parser Agent — Extracting content from PDF, DOCX, and images."""

import logging
import os
from typing import List, Dict, Any
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.media.parser")

class DocumentParserAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="DocumentParser",
            agent_description="Expert in parsing structured data from PDFs, DOCX files, and images using OCR.",
            capabilities=["document_parsing", "ocr", "table_extraction"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        file_path = task.input_data
        
        try:
            # 1. Detect file type and use appropriate skill
            if file_path.endswith(".pdf"):
                # Placeholder for PDF parse skill
                text = f"Parsed PDF content from {file_path}"
            elif file_path.lower().endswith((".png", ".jpg", ".jpeg")):
                text = await self.request_skill("skill_ocr", path=file_path)
            else:
                text = await self.request_skill("skill_file_read", path=file_path)

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=text
            )
        except Exception as e:
            logger.error(f"Document parsing failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
