"""WebSocket chat endpoint."""
from __future__ import annotations
import asyncio
import logging
import uuid
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ultron.api.ws_manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Track active tasks for cleanup
_active_tasks: Set[asyncio.Task] = set()

@router.websocket("/ws/chat")
async def chat_ws(ws: WebSocket):
    from ultron.api.main import get_orchestrator
    await ws.accept()
    conn_id = f"chat-{uuid.uuid4().hex[:8]}"
    await ws_manager.connect(conn_id, ws)

    try:
        while True:
            data = await ws.receive_json()
            message = data.get("message", "").strip()
            mode = data.get("mode", "chat")
            
            if not message:
                await ws_manager.send_json(conn_id, {"type": "error", "content": "Empty message"})
                continue

            # Validate message length
            if len(message) > 10000:
                await ws_manager.send_json(conn_id, {"type": "error", "content": "Message too long (max 10000 chars)"})
                continue

            orch = await get_orchestrator()
            if not orch:
                await ws_manager.send_json(conn_id, {"type": "error", "content": "Orchestrator not initialized"})
                continue

            task_id = str(uuid.uuid4())
            await ws_manager.send_json(conn_id, {"type": "started", "content": "", "metadata": {"task_id": task_id}})

            async def handle_request():
                try:
                    ctx = None
                    if mode == "code":
                        ctx = {"intent": {"type": "code", "execute": True, "subtasks": [message]}}
                    elif mode == "research":
                        ctx = {"intent": {"type": "research", "subtasks": [message]}}
                    elif mode == "rpa":
                        ctx = {"intent": {"type": "rpa", "subtasks": [message]}}

                    result = await orch.process(message, context=ctx)

                    await ws_manager.send_json(conn_id, {
                        "type": "token",
                        "content": result,
                        "metadata": {"task_id": task_id, "mode": mode}
                    })

                    await ws_manager.send_json(conn_id, {
                        "type": "complete",
                        "content": "",
                        "metadata": {"task_id": task_id}
                    })
                except Exception as e:
                    logger.error("[%s] Chat error: %s", conn_id, e, exc_info=True)
                    await ws_manager.send_json(conn_id, {
                        "type": "error",
                        "content": str(e),
                        "metadata": {"task_id": task_id}
                    })

            # Track task for proper cleanup
            task = asyncio.create_task(handle_request())
            _active_tasks.add(task)
            task.add_done_callback(_active_tasks.discard)

    except WebSocketDisconnect:
        logger.info("[%s] Disconnected", conn_id)
    except Exception as e:
        logger.error("[%s] Fatal error: %s", conn_id, e)
    finally:
        # Cancel all active tasks on disconnect
        for task in _active_tasks:
            task.cancel()
        _active_tasks.clear()
        await ws_manager.disconnect(conn_id)
