"""Verification test for ULTRON v3.0 Phase 1 Infrastructure."""

import asyncio
import pytest
import os
from ultron.v2.core.base_agent import BaseAgent, AgentTask, AgentResult, AgentStatus
from ultron.v2.core.skill_engine import SkillEngine
from ultron.v2.core.agent_registry import registry
from ultron.v2.core.event_bus import event_bus, Event

class MockAgent(BaseAgent):
    """A mock agent for testing the infrastructure."""
    
    async def execute(self, task: AgentTask) -> AgentResult:
        self.status = AgentStatus.RUNNING
        # Simulate some work
        await asyncio.sleep(0.1)
        
        # Test skill engine if available
        skill_output = None
        if self.skill_engine:
            skill_output = await self.request_skill("skill_system_metrics")
            
        self.status = AgentStatus.IDLE
        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            output={"message": "Mock task completed", "skill_data": skill_output}
        )

    async def health_check(self) -> bool:
        return True

@pytest.mark.asyncio
async def test_v3_infrastructure():
    # 1. Initialize Skill Engine
    engine = SkillEngine()
    
    # 2. Initialize and Register Agent
    agent = MockAgent(
        agent_name="TestAgent",
        agent_description="Agent for infrastructure testing",
        capabilities=["test", "metrics"],
        skill_engine=engine
    )
    registry.register(agent)
    
    # 3. Test Agent Registry
    assert registry.get_agent("TestAgent") == agent
    assert agent in registry.get_agents_by_capability("metrics")
    
    # 4. Test Event Bus
    events_received = []
    async def event_handler(event: Event):
        events_received.append(event)
    
    event_bus.subscribe("test_event", event_handler)
    await event_bus.publish_simple("test_event", "test_source", {"key": "value"})
    
    assert len(events_received) == 1
    assert events_received[0].name == "test_event"
    assert events_received[0].data["key"] == "value"
    
    # 5. Test Agent Execution and Skill Engine
    task = AgentTask(task_type="test_task", input_data="hello")
    result = await agent.execute(task)
    
    assert result.success is True
    assert "cpu_percent" in result.output["skill_data"]
    
    # 6. Test Health Check
    health = await registry.health_check_all()
    assert health["TestAgent"] is True
    
    print("\n[PASS] ULTRON v3.0 Phase 1 Infrastructure Verification PASSED!")

if __name__ == "__main__":
    asyncio.run(test_v3_infrastructure())
