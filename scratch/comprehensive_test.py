import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from ultron.v2.core.agent_registry import registry
from ultron.v2.core.skill_engine import SkillEngine
from ultron.v2.core.event_bus import event_bus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import router
from ultron.v2.core.base_agent import AgentTask
from ultron.v2.core.react_orchestrator import ReActOrchestrator

# Import specific agents to test lazy loading from classes
from ultron.v2.agents.sysmon_agent import SystemMonitorAgent
from ultron.v2.agents.creation.coder_agent_v3 import CoderAgentV3

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("comprehensive_test")

async def run_comprehensive_test():
    logger.info("Starting Comprehensive Agents & Skills Test...")
    
    # 1. Setup Environment
    from dotenv import load_dotenv
    load_dotenv()
    router.enable_all_providers(dict(os.environ))
    
    blackboard = Blackboard()
    skill_engine = SkillEngine()
    
    # 2. Setup Registry with Factory Providers (as main.py does)
    registry.set_factory_provider("llm_router", router)
    registry.set_factory_provider("event_bus", event_bus)
    registry.set_factory_provider("blackboard", blackboard)
    registry.set_factory_provider("skill_engine", skill_engine)
    
    # 3. Register Agents Lazily
    registry.register_lazy("SysMon", "System Monitor", SystemMonitorAgent)
    registry.register_lazy("CoderV3", "Advanced Coder", CoderAgentV3)
    
    logger.info("Agents registered lazily. Testing Skill Engine first...")
    
    # 4. Test Skill Engine directly
    try:
        metrics = await skill_engine.run("skill_system_metrics")
        logger.info(f"Skill Engine Test (Metrics): {metrics}")
        assert "cpu_percent" in metrics
        logger.info("\u2713 Skill Engine: SUCCESS")
    except Exception as e:
        logger.error(f"\u2717 Skill Engine: FAILED - {e}")

    # 5. Test Lazy Agent Instantiation & Execution
    logger.info("Testing SysMon agent (triggers instantiation)...")
    try:
        task = AgentTask(task_type="sysmon", input_data="Current system status")
        sysmon = registry.get_agent("SysMon")
        if sysmon:
            result = await sysmon.execute(task)
            logger.info(f"SysMon Execution Output: {result.output[:100]}...")
            assert result.success
            logger.info("\u2713 SysMon Agent: SUCCESS")
        else:
            logger.error("\u2717 SysMon Agent: NOT FOUND IN REGISTRY")
    except Exception as e:
        logger.error(f"\u2717 SysMon Agent: FAILED - {e}")

    # 6. Test CoderV3 Agent
    logger.info("Testing CoderV3 agent (triggers instantiation)...")
    try:
        task = AgentTask(task_type="coding", input_data="Write a python function that calculates fibonacci.")
        coder = registry.get_agent("CoderV3")
        if coder:
            result = await coder.execute(task)
            logger.info(f"CoderV3 Execution Output: {result.output[:100]}...")
            assert result.success
            logger.info("\u2713 CoderV3 Agent: SUCCESS")
        else:
            logger.error("\u2717 CoderV3 Agent: NOT FOUND IN REGISTRY")
    except Exception as e:
        logger.error(f"\u2717 CoderV3 Agent: FAILED - {e}")

    # 7. Check Registry State
    logger.info("Final Registry State:")
    for agent in registry.list_agents():
        logger.info(f" - {agent['name']}: {agent['status']}")

if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())
