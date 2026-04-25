"""Agent Registry for Ultron v3.0 — Centralized management of agent instances."""

import logging
import inspect
from typing import Any, Dict, List, Optional
from ultron.v2.core.base_agent import BaseAgent, AgentStatus

logger = logging.getLogger("ultron.agent_registry")

class AgentRegistry:
    """Registry to manage all active agent instances in the Ultron system."""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._lazy_metadata: Dict[str, Dict[str, str]] = {}
        self._lazy_classes: Dict[str, type] = {}
        self._factory_providers: Dict[str, Any] = {}

    def set_factory_provider(self, key: str, provider: Any):
        """Set a shared resource provider for lazy instantiation."""
        self._factory_providers[key] = provider

    def register(self, agent: BaseAgent):
        """Register an agent instance."""
        name = getattr(agent, "agent_name", None) or getattr(agent, "name", "UnknownAgent")
        if name in self._agents:
            logger.warning(f"Agent with name {name} already registered. Overwriting.")
        self._agents[name] = agent
        # Clean up lazy registration if it exists
        self._lazy_metadata.pop(name, None)
        self._lazy_classes.pop(name, None)
        logger.info(f"Agent registered: {name}")

    def register_lazy(self, name: str, description: str, agent_cls: type):
        """Register an agent class for lazy instantiation."""
        if name in self._agents:
            return # Already registered as instance
        self._lazy_metadata[name] = {
            "name": name,
            "description": description,
            "status": AgentStatus.IDLE.value if hasattr(AgentStatus.IDLE, "value") else AgentStatus.IDLE
        }
        self._lazy_classes[name] = agent_cls
        logger.debug(f"Agent registered (lazy): {name}")

    def unregister(self, agent_name: str):
        """Unregister an agent instance or lazy class."""
        self._agents.pop(agent_name, None)
        self._lazy_metadata.pop(agent_name, None)
        self._lazy_classes.pop(agent_name, None)
        logger.info(f"Agent unregistered: {agent_name}")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent instance by name, instantiating if lazy."""
        if name in self._agents:
            return self._agents[name]
        
        if name in self._lazy_classes:
            agent_cls = self._lazy_classes[name]
            try:
                # Try to satisfy dependencies from factory providers
                sig = inspect.signature(agent_cls.__init__)
                params = sig.parameters
                
                kwargs = {}
                for p_name, p in params.items():
                    if p_name == 'self': continue
                    if p_name in self._factory_providers:
                        kwargs[p_name] = self._factory_providers[p_name]
                    elif p.default == inspect.Parameter.empty:
                        # Required parameter not in providers
                        # We try common aliases or just let it fail
                        if 'router' in p_name and 'llm_router' in self._factory_providers:
                            kwargs[p_name] = self._factory_providers['llm_router']
                        elif 'bus' in p_name and 'event_bus' in self._factory_providers:
                            kwargs[p_name] = self._factory_providers['event_bus']
                
                instance = agent_cls(**kwargs)
                self.register(instance)
                return instance
            except Exception as e:
                logger.error(f"Failed to instantiate lazy agent {name}: {e}")
        
        return None

    def get_agents_by_capability(self, capability: str) -> List[BaseAgent]:
        """Find all agents that possess a specific capability (forces instantiation for lazy agents)."""
        all_names = set(self._agents.keys()) | set(self._lazy_classes.keys())
        matches = []
        for name in all_names:
            agent = self.get_agent(name)
            if agent and hasattr(agent, "capabilities") and capability in agent.capabilities:
                matches.append(agent)
        return matches

    def list_agents(self) -> List[Dict[str, str]]:
        """List all registered agents (including lazy ones without instantiating)."""
        active = [
            {
                "name": getattr(agent, "agent_name", "Unknown"),
                "id": getattr(agent, "agent_id", "Unknown"),
                "status": agent.status.value if hasattr(agent.status, "value") else agent.status,
                "description": getattr(agent, "agent_description", "No description")
            }
            for agent in self._agents.values()
        ]
        lazy = list(self._lazy_metadata.values())
        return active + lazy

    async def start_all(self):
        """Start all registered agents."""
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
