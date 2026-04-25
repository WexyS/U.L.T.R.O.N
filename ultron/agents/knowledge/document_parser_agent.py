"""DocumentParserAgent — RAG-enabled document analysis and summarization."""

import os
import logging
from typing import Dict, Any, List, Optional
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router
from pypdf import PdfReader

logger = logging.getLogger("ultron.agents.knowledge.doc_parser")

class DocumentParserAgent(BaseAgent):
    agent_name = "DocumentParserAgent"
    agent_description = "Parses and understands various document formats."

    """Parses and understands various document formats."""

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="DocumentParserAgent",
            agent_description="Expert at reading and extracting knowledge from PDFs, Word docs, and more.",
            capabilities=["pdf_parsing", "document_summarization", "rag_search", "text_extraction"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        
        file_path = task.input_data.get("file_path")
        mode = task.input_data.get("mode", "summarize") # summarize, ask, extract
        
        if not file_path or not os.path.exists(file_path):
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="File not found.")

        try:
            # 1. Extraction
            text = self._extract_text(file_path)
            
            # 2. Process based on mode
            if mode == "summarize":
                output = await self._summarize(text)
            elif mode == "ask":
                question = task.input_data.get("question", "")
                output = await self._ask_question(text, question)
            else:
                output = {"text_preview": text[:1000]}

            self.status = AgentStatus.IDLE
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=output
            )
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"DocumentParserAgent failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))

    def _extract_text(self, path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            reader = PdfReader(path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        elif ext in [".txt", ".md"]:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            raise ValueError(f"Unsupported extension: {ext}")

    async def _summarize(self, text: str) -> str:
        # Simple chunking for very long docs
        truncated_text = text[:10000] 
        prompt = f"Summarize the following document content concisely:\n\n{truncated_text}"
        resp = await router.chat([{"role": "user", "content": prompt}], preferred_provider="gemini")
        return resp.content

    async def _ask_question(self, text: str, question: str) -> str:
        truncated_text = text[:15000]
        prompt = f"Using the following document content, answer the question: {question}\n\nCONTENT:\n{truncated_text}"
        resp = await router.chat([{"role": "user", "content": prompt}], preferred_provider="gemini")
        return resp.content

    async def health_check(self) -> bool:
        return True
