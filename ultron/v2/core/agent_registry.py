"""Agent Registry for Ultron v3.0 — Centralized management of agent instances."""

import logging
from typing import Dict, List, Optional
from ultron.v2.core.base_agent import BaseAgent, AgentStatus

logger = logging.getLogger("ultron.agent_registry")

class AgentRegistry:
    """Registry to manage all active agent instances in the Ultron system."""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent):
        """Register an agent instance."""
        if agent.agent_name in self._agents:
            logger.warning(f"Agent with name {agent.agent_name} already registered. Overwriting.")
        self._agents[agent.agent_name] = agent
        logger.info(f"Agent registered: {agent.agent_name} ({agent.agent_id})")

    def unregister(self, agent_name: str):
        """Unregister an agent instance."""
        if agent_name in self._agents:
            del self._agents[agent_name]
            logger.info(f"Agent unregistered: {agent_name}")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent instance by name."""
        return self._agents.get(name)

    def get_agents_by_capability(self, capability: str) -> List[BaseAgent]:
        """Find all agents that possess a specific capability."""
        return [
            agent for agent in self._agents.values()
            if capability in agent.capabilities
        ]

    def list_agents(self) -> List[Dict[str, str]]:
        """List all registered agents and their basic info."""
        return [
            {
                "name": agent.agent_name,
                "id": agent.agent_id,
                "status": agent.status,
                "description": agent.agent_description
            }
            for agent in self._agents.values()
        ]

    async def start_all(self):
        """Start all registered agents (placeholder for complex initialization)."""
        for agent in self._agents.values():
            if agent.status == AgentStatus.DISABLED:
                continue
            agent.status = AgentStatus.IDLE
        logger.info("All capable agents started.")

    async def stop_all(self):
        """Stop all registered agents."""
        for agent in self._agents.values():
            agent.status = AgentStatus.DISABLED
        logger.info("All agents stopped.")

    async def health_check_all(self) -> Dict[str, bool]:
        """Run health checks on all registered agents."""
        results = {}
        for name, agent in self._agents.items():
            try:
                results[name] = await agent.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = False
        return results

# Global registry instance
registry = AgentRegistry()
