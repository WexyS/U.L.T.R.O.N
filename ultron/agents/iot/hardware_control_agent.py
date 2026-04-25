"""Hardware Control Agent — Interacting with mouse, keyboard, and peripherals."""

import logging
import pyautogui
from ultron.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus

logger = logging.getLogger("ultron.agents.iot.hardware")

class HardwareControlAgent(BaseAgent):
    agent_name = "HardwareControlAgent"
    agent_description = "Specialized Genesis agent for HardwareControl tasks."

    def __init__(self, memory=None, skill_engine=None):
        super().__init__(
            agent_name="HardwareControl",
            agent_description="Directly interacts with system hardware, mouse, and keyboard for automation tasks.",
            capabilities=["mouse_control", "keyboard_control", "peripheral_management"],
            memory=memory,
            skill_engine=skill_engine
        )
        pyautogui.FAILSAFE = True

    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        command = task.task_type # move_to, click, type_text
        
        try:
            if command == "move_to":
                x, y = task.input_data.get("x"), task.input_data.get("y")
                pyautogui.moveTo(x, y, duration=0.5)
            elif command == "click":
                pyautogui.click()
            elif command == "type_text":
                pyautogui.write(task.input_data.get("text", ""))
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=f"Hardware command '{command}' executed."
            )
        except Exception as e:
            logger.error(f"Hardware control failed: {e}")
            return AgentResult(task_id=task.task_id, agent_id=self.agent_id, success=False, error=str(e))
        finally:
            self.status = AgentStatus.IDLE

    async def health_check(self) -> bool:
        return True
