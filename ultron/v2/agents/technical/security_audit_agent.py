"""Security Audit Agent — Reviewing code and configurations for vulnerabilities."""

import logging
import json
import re
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.llm_router import router

logger = logging.getLogger("ultron.agents.technical.security")

class SecurityAuditAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="SecurityAudit",
            agent_description="Expert in cybersecurity, performing deep audits on code, APIs, and system configurations.",
            capabilities=["security_audit", "vulnerability_detection", "threat_modeling"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        target = task.input_data # Code or config string

        try:
            prompt = [
                {"role": "system", "content": "You are a senior security researcher. Conduct a thorough security audit of the provided content. Identify vulnerabilities (OWASP Top 10), misconfigurations, and sensitive data leaks. Return JSON: {\"vulnerabilities\": [{\"severity\": \"High\", \"description\": \"...\", \"fix\": \"...\"}], \"overall_risk\": \"...\"}"},
                {"role": "user", "content": f"Target Content:\n{target}"}
            ]
            resp = await router.chat(prompt)
            
            match = re.search(r"\{[\s\S]*\}", resp.content)
            if match:
                audit_result = json.loads(match.group())
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=True,
                    output=audit_result
                )
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error="Security audit failed.")
        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
