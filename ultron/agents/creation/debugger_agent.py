"""DebuggerAgent — Autonomous error analysis and self-healing engine."""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.creation.debugger")

class DebuggerAgent(BaseAgent):
    agent_name = "DebuggerAgent"
    agent_description = "Analyzes stack traces and provides fixes."

    """Analyzes stack traces and provides fixes."""

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="DebuggerAgent",
            agent_description="Expert system for autonomous error analysis and code fixing.",
            capabilities=["error_analysis", "root_cause_analysis", "python_debugging", "js_debugging", "sql_debugging"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        """Analyze an error and provide suggested fixes."""
        self.status = AgentStatus.RUNNING
        
        error_message = task.input_data.get("error_message", "")
        code = task.input_data.get("code", "")
        language = task.input_data.get("language", "python")
        context = task.input_data.get("context", "General execution")

        if not error_message:
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error="No error message provided."
            )

        # 1. Classification & LLM Prompting
        prompt = f"""
You are an expert Debugger Agent. Analyze the following error and provide root causes and fixes.

CONTEXT: {context}
LANGUAGE: {language}
ERROR MESSAGE:
{error_message}

CODE SNIPPET:
{code}

Return ONLY a JSON object with this structure:
{{
  "error_type": "...",
  "root_cause": "...",
  "fixes": [
    {{"description": "...", "code": "...", "confidence": 0.95}}
  ],
  "prevention_tips": ["...", "..."],
  "best_fix_index": 0
}}
"""
        try:
            resp = await router.chat([{"role": "user", "content": prompt}], preferred_provider="deepseek")
            
            # Clean JSON
            content = re.sub(r"```json\n?|\n?```", "", resp.content).strip()
            analysis = json.loads(content)
            
            self.status = AgentStatus.IDLE
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=analysis
            )
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"DebuggerAgent failed: {e}")
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error=str(e)
            )

    async def health_check(self) -> bool:
        return True
