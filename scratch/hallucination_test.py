import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from ultron.v2.core.react_orchestrator import ReActOrchestrator
from ultron.v2.core.base_agent import AgentTask
from ultron.v2.core.agent_registry import registry
from ultron.v2.core.event_bus import event_bus
from ultron.v2.core.blackboard import Blackboard
from ultron.v2.core.llm_router import router

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("hallucination_test")

async def run_test():
    logger.info("Starting Hallucination & Intelligence Test...")
    
    # 0. Load Environment and Initialize Router
    from dotenv import load_dotenv
    load_dotenv()
    router.enable_all_providers(dict(os.environ))
    
    # Initialize shared resources for agents
    blackboard = Blackboard()
    
    # Configure registry with shared resources
    registry.set_factory_provider("llm_router", router)
    registry.set_factory_provider("event_bus", event_bus)
    registry.set_factory_provider("blackboard", blackboard)
    
    # 1. Initialize Registry and Orchestrator
    orchestrator = ReActOrchestrator()
    registry.register(orchestrator)
    
    # Mock some agents if they are not available to avoid heavy initialization,
    # but for a real test we want the real ones.
    # However, since we are in a headless environment, we might need to mock ImageGeneration.
    
    from ultron.v2.agents.researcher import ResearcherAgent
    from ultron.v2.agents.creative.image_generation_agent import ImageGenerationAgent
    
    # We use registry.register_lazy (our new feature!)
    registry.register_lazy("ResearcherAgent", "Does research", ResearcherAgent)
    registry.register_lazy("ImageGenerationAgent", "Generates images", ImageGenerationAgent)
    
    # 2. Listen for steps to observe thinking process
    async def on_step(event):
        step = event.data
        logger.info(f"STEP [{step['type'].upper()}] (Agent: {step['agent']}): {step['content'][:200]}... [Latency: {step['latency_ms']}ms]")

    event_bus.subscribe("orchestrator_step", on_step)
    
    # 3. Define the complex task
    task = AgentTask(
        task_type="complex_request",
        input_data="Nvidia'nın 2024 son çeyrek gelirlerini araştır, bir özet yaz ve ardından bu geliri temsil eden bir görsel oluştur.",
        context={"user_name": "Eren"}
    )
    
    logger.info(f"Executing task: {task.input_data}")
    
    # 4. Execute
    # Note: This requires a working LLM provider (Ollama or similar).
    # If not available, it will fail or use mocks if we provide them.
    try:
        result = await orchestrator.execute(task)
        
        logger.info("=" * 60)
        logger.info("FINAL RESULT:")
        logger.info(result.output)
        logger.info("=" * 60)
        logger.info(f"Success: {result.success}")
        logger.info(f"Tools Used: {result.tools_used}")
        logger.info(f"Latency: {result.latency_ms}ms")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_test())
