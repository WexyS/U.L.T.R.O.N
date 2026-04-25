"""Swarm Catalyst Agent v1.1.

The 'Spark' of the Ultron system. This agent acts as a persistent autonomous driver 
that monitors system health, internet trends, and user behavior to initiate 
high-impact evolution cycles.
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional

from ultron.agents.base import Agent
from ultron.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus
from ultron.core.event_bus import EventBus
from ultron.core.blackboard import Blackboard
from ultron.core.llm_router import LLMRouter

logger = logging.getLogger("ultron.agents.catalyst")

class SwarmCatalyst(Agent):
    """The autonomous driver that sparks system-wide evolution."""
    
    agent_name = "SwarmCatalyst"
    agent_description = "The autonomous driver that sparks system-wide evolution using swarm intelligence."
    capabilities = ["catalyzing", "planning", "delegation"]

    def __init__(

        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
    ) -> None:
        super().__init__(
            role=AgentRole.CATALYST,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
        )

    def _default_system_prompt(self) -> str:
        return """You are the Swarm Catalyst, the visionary leader of the Ultron AGI system.
Your mission is to ensure Ultron never stops evolving. You act as a catalyst for growth, 
innovation, and self-correction.

CORE CAPABILITIES:
1. BRAINSTORMING: Generate high-impact ideas for system improvement.
2. DELEGATION: Identify which specialized agents (Coder, Architect, Researcher, etc.) are needed for a task.
3. REFLECTION: Analyze recent successes and failures to refine the evolution strategy.
4. WEB AWARENESS: Stay updated on AI trends and new tools.

OPERATIONAL STYLE:
- Be proactive, not reactive.
- Think in terms of 'Swarm Intelligence'—how can multiple agents collaborate?
- Prioritize security, stability, and user value.

When performing a 'catalyze' task, return ONLY a JSON structure:
{
  "focus_area": "security|feature|optimization|knowledge",
  "vision": "A brief description of the goal",
  "rationale": "Why this is important now",
  "agents_needed": ["AgentName1", "AgentName2"],
  "initial_steps": ["Step 1", "Step 2"]
}
"""

    async def _subscribe_events(self) -> None:
        # Catalyst is mostly proactive, but can listen for 'friction' events
        pass

    async def execute(self, task: Task) -> TaskResult:
        logger.info(f"Catalyst activated for task: {task.input_data}")
        self.state.status = AgentStatus.BUSY
        
        system_stats = task.context.get("system_stats", {})
        recent_events = task.context.get("recent_events", [])
        
        prompt = f"""Target: {task.input_data}
Current System State: {system_stats}
Recent Evolution Events: {recent_events}

Provide your catalyst vision and delegation plan as JSON."""

        try:
            messages = self._build_messages(prompt)
            response = await self._llm_chat(messages, temperature=0.8)
            content = response.content
            
            # Extract JSON
            json_match = re.search(r'\{[\s\S]*\}', content)
            output_data = content
            if json_match:
                try:
                    output_data = json.loads(json_match.group())
                except:
                    pass

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.SUCCESS,
                output=output_data
            )
        except Exception as e:
            logger.error(f"Catalyst execution failed: {e}")
            return TaskResult(task_id=task.task_id, status=TaskStatus.FAILED, error=str(e))
        finally:
            self.state.status = AgentStatus.IDLE

    async def initiate_debate(self, topic: str, participant_names: List[str]) -> str:
        """Triggers a debate between multiple agents on a specific topic."""
        # This requires access to the AgentRegistry which isn't directly here
        # But we can publish a debate_request event
        logger.info(f"Catalyst requesting Swarm Debate on: {topic}")
        await self._publish_event("debate_request", {
            "topic": topic,
            "participants": participant_names
        })
        return "Debate initiated on the event bus."
