"""Debugger Agent — Analyzing errors and proposing fixes."""

import logging
import json
import re
from typing import Dict, Any
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.creation.debugger")

class DebuggerAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="DebuggerAgent",
            agent_description="Specializes in analyzing stack traces, identifying root causes, and providing code fixes.",
            capabilities=["debugging", "error_analysis", "code_fix"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        error_info = task.input_data
        code_context = task.context.get("code", "")
        language = task.context.get("language", "python")

        try:
            prompt = [
                {"role": "system", "content": f"You are an expert debugger for {language}. Analyze the error and code. Provide a root cause analysis and a fix. Return JSON: {{\"error_type\": \"...\", \"root_cause\": \"...\", \"fix_code\": \"...\", \"explanation\": \"...\", \"prevention_tips\": \"...\"}}"},
                {"role": "user", "content": f"Error: {error_info}\nCode:\n{code_context}"}
            ]
            resp = await router.chat(prompt)
            
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                debug_result = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=debug_result
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Could not parse debug result.")
        except Exception as e:
            logger.error(f"Debugging failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
