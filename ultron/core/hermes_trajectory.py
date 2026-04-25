"""Hermes execution trajectory — records the full Thought-Action-Observation history."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

@dataclass
class ExecutionTrajectory:
    query: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    final_answer: str = ""
    status: str = "running"
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    def add_step(self, thought="", action="", action_input=None, observation=None, error=None):
        s = {"thought":thought,"action":action,"action_input":action_input,"observation":observation,"error":error,"timestamp":datetime.now().isoformat()}
        self.steps.append(s)
        if action and action not in self.tools_called:
            self.tools_called.append(action)

    def summary(self) -> str:
        lines = [f"Query: {self.query}", f"Status: {self.status}", f"Steps: {len(self.steps)}", f"Tools: {', '.join(self.tools_called) if self.tools_called else 'none'}"]
        if self.final_answer: lines.append(f"Answer: {self.final_answer[:200]}")
        return "\n".join(lines)
