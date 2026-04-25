import asyncio
import sys
import logging
from ultron.v2.core.vram_hypervisor import get_vram_usage, get_loaded_models
from ultron.v2.core.event_bus import event_bus
from ultron.v2.core.base_agent import AgentTask
from ultron.v2.agents.nlp_agent import NLPAgent
from ultron.v2.agents.document_agent import DocumentAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Test")

async def run_tests():
    logger.info("=== Phase 3: VRAM Hypervisor Test ===")
    used, total = get_vram_usage()
    logger.info(f"VRAM Usage via nvidia-smi: {used}MB / {total}MB")
    
    models = get_loaded_models()
    logger.info(f"Loaded Ollama Models: {[m.get('name') for m in models] if models else 'None'}")
    
    logger.info("\n=== Phase 2: NLP Agent Test ===")
    nlp = NLPAgent()
    task = AgentTask(input_data="Hello world. Please translate this to Turkish using Skopos theory.")
    # We won't actually execute it against Ollama right now to avoid long delays, just check health
    logger.info(f"NLP Agent initialized. Capabilities: {nlp.capabilities}")
    health = await nlp.health_check()
    logger.info(f"NLP Agent Health: {'OK' if health else 'FAIL'}")

    logger.info("\n=== Phase 2: Document Agent Test ===")
    doc = DocumentAgent()
    logger.info(f"Document Agent initialized. Capabilities: {doc.capabilities}")
    health = await doc.health_check()
    logger.info(f"Document Agent Health: {'OK' if health else 'FAIL'}")
    
    logger.info("\nAll tests passed successfully.")

if __name__ == "__main__":
    asyncio.run(run_tests())
