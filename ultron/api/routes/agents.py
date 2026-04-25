"""REST endpoints for agent invocation."""
from __future__ import annotations
import asyncio
import logging
from fastapi import APIRouter, HTTPException
from ultron.api.models import AgentRequest
from ultron.core.types import AgentRole, Task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])

ROLE_MAP = {"coder": AgentRole.CODER, "researcher": AgentRole.RESEARCHER, "rpa": AgentRole.RPA_OPERATOR}

@router.post("/invoke")
async def invoke_agent(req: AgentRequest):
    from ultron.api.main import get_orchestrator
    orch = await get_orchestrator()
    if not orch:
        raise HTTPException(503, "Orchestrator not initialized")
    role = ROLE_MAP.get(req.agent)
    if not role or role not in orch.agents:
        raise HTTPException(404, f"Agent '{req.agent}' not found")
    agent = orch.agents[role]
    task = Task(description=req.task, intent=req.agent, context=req.context)
    try:
        result = await asyncio.wait_for(agent.execute(task), timeout=300)
        return {"agent": req.agent, "status": result.status.value, "output": (result.output or "")[:5000], "error": result.error[:500] if result.error else None, "metadata": result.metadata}
    except asyncio.TimeoutError:
        raise HTTPException(504, "Agent execution timed out (5 min)")
    except Exception as e:
        raise HTTPException(500, f"Agent error: {e}")

@router.get("/status")
async def agents_status():
    orch = await get_orchestrator()
    if not orch:
        return {"agents": {}}
    result = {}
    for role, agent in orch.agents.items():
        result[role.value] = {"status": agent.state.status.value, "current_task": agent.state.current_task, "tasks_completed": agent.state.tasks_completed, "tasks_failed": agent.state.tasks_failed}
    return result
