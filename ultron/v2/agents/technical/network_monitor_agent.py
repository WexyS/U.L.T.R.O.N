"""Network Monitor Agent — Tracking network connectivity and speed."""

import logging
import httpx
import time
from typing import List, Dict, Any
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus

logger = logging.getLogger("ultron.agents.technical.network")

class NetworkMonitorAgent(BaseAgent):
    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="NetworkMonitor",
            agent_description="Monitors network connectivity, measures latency, and checks the status of external services.",
            capabilities=["network_monitoring", "latency_test", "service_status"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        target_url = task.input_data or "https://www.google.com"

        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(target_url)
                latency = (time.time() - start_time) * 1000
                
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "status_code": resp.status_code,
                    "latency_ms": latency,
                    "target": target_url
                }
            )
        except Exception as e:
            logger.error(f"Network monitor failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
