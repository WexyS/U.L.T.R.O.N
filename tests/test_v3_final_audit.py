"""Final Audit Test for Ultron v3.0 — Verifying all New Agents and Security."""

import asyncio
import os
import json
import logging
import pandas as pd
from datetime import datetime
from ultron.v2.core.agent_registry import registry
from ultron.v2.core.base_agent import AgentTask
from ultron.v2.core.security import ssrf_guard
from ultron.v2.skills.skill_code_sandbox import sandbox

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ultron.tests.final")

async def test_debugger():
    logger.info("--- Testing DebuggerAgent ---")
    agent = registry.get_agent("DebuggerAgent")
    task = AgentTask(input_data={
        "error_message": "IndexError: list index out of range",
        "code": "l = [1, 2]\nprint(l[5])",
        "language": "python"
    })
    result = await agent.execute(task)
    logger.info(f"Debugger Result Success: {result.success}")
    if result.success:
        logger.info(f"Fix: {result.output.get('fixes', [{}])[0].get('description')}")

async def test_calendar():
    logger.info("--- Testing CalendarTaskAgent ---")
    agent = registry.get_agent("CalendarTaskAgent")
    # Add task
    await agent.execute(AgentTask(input_data={
        "intent": "add task",
        "params": {"title": "Test Ultron v3", "priority": 5}
    }))
    # Get briefing
    result = await agent.execute(AgentTask(input_data={"intent": "briefing"}))
    logger.info(f"Calendar Briefing: {result.output}")

async def test_data_analysis():
    logger.info("--- Testing DataAnalysisAgent ---")
    # Create dummy CSV
    csv_path = "data/test_data.csv"
    df = pd.DataFrame({"A": [1, 2, 3], "B": [10, 20, 30]})
    df.to_csv(csv_path, index=False)
    
    agent = registry.get_agent("DataAnalysisAgent")
    task = AgentTask(input_data={"file_path": csv_path, "question": "What's the average of B?"})
    result = await agent.execute(task)
    logger.info(f"Data Analysis Success: {result.success}")
    if result.success:
        logger.info(f"Chart saved: {result.output.get('chart_path')}")

async def test_security():
    logger.info("--- Testing SSRFGuard ---")
    safe = ssrf_guard.is_safe_url("https://google.com")
    unsafe = ssrf_guard.is_safe_url("http://127.0.0.1:8000/admin")
    logger.info(f"SSRF Safety Check -> Google Safe: {safe}, Localhost Unsafe: {not unsafe}")

async def test_sandbox():
    logger.info("--- Testing CodeSandbox ---")
    result = await sandbox.execute_python("print('Hello from Sandbox')")
    logger.info(f"Sandbox Result: {result.get('stdout').strip()}")

async def test_api_agents():
    logger.info("--- Testing API Endpoint /api/v3/agents ---")
    from ultron.api.main import get_all_agents
    agents = await get_all_agents()
    logger.info(f"Found {len(agents)} agents in registry.")
    for a in agents[:3]:
        logger.info(f"Agent: {a['agent_name']} (Status: {a['status']})")

async def run_audit():
    # Populate registry via lifespan
    from ultron.api.main import lifespan
    from fastapi import FastAPI
    app = FastAPI()
    
    async with lifespan(app):
        await test_debugger()
        await test_calendar()
        await test_data_analysis()
        await test_security()
        await test_sandbox()
        await test_api_agents()

if __name__ == "__main__":
    asyncio.run(run_audit())
