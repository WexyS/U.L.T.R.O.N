"""Ultron v3.0 Full System Integration Test."""

import asyncio
import logging
from ultron.v2.core.agent_registry import registry
from ultron.v2.core.react_orchestrator import ReActOrchestrator
from ultron.v2.core.base_agent import AgentTask
from ultron.v2.agents.cognitive.task_decomposer import TaskDecomposerAgent
from ultron.v2.agents.knowledge.enhanced_researcher import EnhancedResearcherAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ultron.test.v3")

async def test_v3_flow():
    logger.info("Starting Ultron v3.0 Integration Test...")

    # 1. Initialize Registry and Core Agents
    orch = ReActOrchestrator()
    registry.register(orch)
    registry.register(TaskDecomposerAgent())
    registry.register(EnhancedResearcherAgent())
    
    logger.info(f"Registered Agents: {registry.list_agents()}")

    # 2. Execute a Simple Multi-Agent Task
    task_desc = "Hello Ultron! Introduce yourself briefly."
    task = AgentTask(task_type="user_request", input_data=task_desc)
    
    logger.info(f"Submitting Task: {task_desc}")
    result = await orch.execute(task)
    
    if result.success:
        logger.info("✅ V3.0 Integration Test SUCCESS!")
        logger.info(f"Output: {result.output}")
    else:
        logger.error(f"❌ V3.0 Integration Test FAILED: {result.error}")

if __name__ == "__main__":
    asyncio.run(test_v3_flow())
