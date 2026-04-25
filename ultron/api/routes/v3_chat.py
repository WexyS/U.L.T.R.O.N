"""Ultron v3.0 Chat & WebSocket Routes."""

import logging
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ultron.core.event_bus import event_bus
from ultron.core.base_agent import AgentTask
from ultron.core.react_orchestrator import ReActOrchestrator
from ultron.core.agent_registry import registry

router = APIRouter(prefix="/api/v3", tags=["Ultron v3.0"])
logger = logging.getLogger("ultron.api.v3")

# ── WebSocket Manager ──────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Connection might be dead
                pass

manager = ConnectionManager()

# Hook EventBus into WebSocket broadcast
async def ws_event_bridge(event_dict: Dict[str, Any]):
    await manager.broadcast({"type": "event", "data": event_dict})

event_bus.set_ws_bridge(ws_event_bridge)

# ── Routes ─────────────────────────────────────────────────────────────

@router.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

class V3ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

@router.post("/chat")
async def v3_chat(req: V3ChatRequest):
    """Execute a task using the v3.0 ReAct Orchestrator."""
    orchestrator = registry.get_agent("ReActOrchestrator")
    if not orchestrator:
        # Fallback: Initialize if not exists
        orchestrator = ReActOrchestrator()
        registry.register(orchestrator)
    
    task = AgentTask(
        task_type="user_request",
        input_data=req.message,
        context=req.context or {}
    )
    
    # Run in background to not block, but for this endpoint we'll await result
    result = await orchestrator.execute(task)
    
    return {
        "success": result.success,
        "output": result.output,
        "latency_ms": result.latency_ms,
        "agent_id": result.agent_id
    }

@router.get("/agents")
async def list_v3_agents():
    """List all registered v3.0 agents."""
    return registry.list_agents()

@router.get("/skills")
async def list_skills():
    """List all discovered skills."""
    from ultron.core.skill_manager import discover_all_skills
    return discover_all_skills()

@router.get("/external-agents")
async def list_external_agents():
    """List all discovered external (non-core) agents."""
    from ultron.core.skill_manager import discover_all_agents
    return discover_all_agents()
