"""System Admin Agent — Managing local system resources and configurations."""

import logging
import psutil
from typing import List, Dict, Any
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus

logger = logging.getLogger("ultron.agents.technical.sysadmin")

class SystemAdminAgent(BaseAgent):
    agent_name = "SystemAdminAgent"
    agent_description = "Specialized Genesis agent for SystemAdmin tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="SystemAdmin",
            agent_description="Manages local system resources, monitors health, and assists with system-level configurations.",
            capabilities=["system_monitoring", "process_management", "resource_optimization"],
            memory=memory,
            skill_engine=skill_engine
        )

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        action = task.task_type # metrics, list_processes, kill_process
        
        try:
            if action == "metrics":
                result = self._get_metrics()
            elif action == "list_processes":
                result = self._list_processes()
            else:
                result = "Unknown sysadmin action."

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=result
            )
        except Exception as e:
            logger.error(f"System admin operation failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    def _get_metrics(self) -> Dict[str, Any]:
        return {
            "cpu": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage("/")._asdict()
        }

    def _list_processes(self) -> List[Dict[str, Any]]:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes[:20] # Return top 20 for brevity

    async def health_check(self) -> bool:
        return True
