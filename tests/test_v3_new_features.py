"""Integration Test for Ultron v3.0 New Features."""

import asyncio
import os
import json
import logging
from datetime import datetime
from ultron.core.agent_registry import registry
from ultron.core.llm_router import router
from ultron.core.react_orchestrator import ReActOrchestrator
from ultron.core.base_agent import AgentTask

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ultron.tests.v3")

async def test_intelligence_core():
    logger.info("--- Testing Intelligence Core (Reasoning & Personality) ---")
    orchestrator = registry.get_agent("ReActOrchestrator")
    if not orchestrator:
        logger.error("ReActOrchestrator not found in registry!")
        return

    # Test Case: Complex Problem Solving
    task = AgentTask(
        task_id="test_reasoning",
        input_data="Tren saatte 120km gidiyor. 2 saat sonra başka tren 180km ile aynı yöne çıkıyor. Ne zaman yetişir?"
    )
    result = await orchestrator.execute(task)
    
    logger.info(f"Reasoning Result Success: {result.success}")
    logger.info(f"Final Answer: {result.output[:100]}...")
    
    # Verify Personality
    if "ULTRON" in result.output or "asistan" in result.output.lower():
        logger.info("Personality check passed.")
    else:
        logger.warning("Personality check failed (ULTRON identity not found in response).")

async def test_creative_agents():
    logger.info("--- Testing Creative Agents (Image Gen) ---")
    agent = registry.get_agent("ImageGenerationAgent")
    if not agent:
        logger.error("ImageGenerationAgent not found!")
        return

    task = AgentTask(
        task_id="test_img_gen",
        input_data="A futuristic city in space",
        context={"style": "cyberpunk"}
    )
    result = await agent.execute(task)
    logger.info(f"Image Gen Result: {result.success}")
    if result.success:
        logger.info(f"Saved Image: {result.output.get('image_path')}")

async def test_data_pipeline():
    logger.info("--- Testing Data Pipeline ---")
    from scripts.data_pipeline.harvest_conversations import ConversationHarvester
    harvester = ConversationHarvester()
    harvested = harvester.harvest()
    logger.info(f"Harvested {len(harvested)} samples.")

async def test_upgraded_agents():
    logger.info("--- Testing Upgraded Agents (Calendar & Data) ---")
    calendar = registry.get_agent("CalendarTaskAgent")
    if calendar:
        task = AgentTask(input_data="Bugün ne yapmam gerekiyor?")
        result = await calendar.execute(task)
        logger.info(f"Calendar Briefing: {result.success}")
    
    data_agent = registry.get_agent("DataAnalysisAgent")
    if data_agent:
        logger.info("DataAnalysisAgent check passed.")

async def run_all_tests():
    # Make sure registry is populated
    from ultron.api.main import lifespan
    from fastapi import FastAPI
    app = FastAPI()
    
    async with lifespan(app):
        await test_intelligence_core()
        await test_upgraded_agents()
        await test_creative_agents()
        await test_data_pipeline()

if __name__ == "__main__":
    asyncio.run(run_all_tests())
