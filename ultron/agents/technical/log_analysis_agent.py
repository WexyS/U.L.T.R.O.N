"""Log Analysis Agent — Identifying patterns and anomalies in system logs."""

import logging
import json
import re
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.agents.technical.logs")

class LogAnalysisAgent(BaseAgent):
    agent_name = "LogAnalysisAgent"
    agent_description = "Specialized Genesis agent for LogAnalysis tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="LogAnalysis",
            agent_description="Expert in log analysis, identifying patterns, errors, and security anomalies in large log files.",
            capabilities=["log_parsing", "anomaly_detection", "pattern_recognition"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        log_content = task.input_data

        try:
            prompt = [
                {"role": "system", "content": "Analyze the provided log content. Identify critical errors, warnings, recurring patterns, and potential security threats. Return JSON: {\"errors\": [], \"warnings\": [], \"anomalies\": [], \"summary\": \"...\"}"},
                {"role": "user", "content": f"Logs:\n{log_content[:5000]}"} # Limit for LLM context
            ]
            resp = await router.chat(prompt)
            
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                analysis = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=analysis
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Log analysis failed.")
        except Exception as e:
            logger.error(f"Log analysis failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
