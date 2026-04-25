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


@router.websocket("/ws/chat")
async def chat_ws(ws: WebSocket):
    from ultron.api.main import get_orchestrator

    # Set longer timeout for WebSocket
    await ws.accept()
    conn_id = f"chat-{uuid.uuid4().hex[:8]}"
    logger.info("[%s] WebSocket connected", conn_id)

    await ws_manager.connect(conn_id, ws)

    # SECURITY FIX: Track tasks per-connection instead of globally
    conn_tasks: Set[asyncio.Task] = set()

    try:
        while True:
            try:
                # Remove artificial timeout; receive_json() will raise WebSocketDisconnect when closed
                data = await ws.receive_json()
            except Exception as e:
                logger.warning("[%s] Receive error: %s", conn_id, e)
                break

            # Handle ping/heartbeat messages
            if data.get("type") == "ping":
                await ws_manager.send_json(conn_id, {"type": "pong"})
                continue

            message = data.get("message", "").strip()
            mode = data.get("mode", "chat")
            history = data.get("history", [])
            conversation_id = data.get("conversation_id")

            if not message:
                # If it's not a ping and has no message, just ignore it
                continue

            # Persistence: Save user message
            from ultron.memory.conversation_store import ConversationStore
            store = ConversationStore()
            if conversation_id:
                try:
                    store.add_message(conversation_id, "user", message)
                except Exception as e:
                    logger.warning("[%s] Failed to save user message: %s", conn_id, e)

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

                    if ctx is None:
                        ctx = {}
                    ctx["history"] = history
                    ctx["conversation_id"] = conversation_id

                    result = await orch.process(message, context=ctx)

                    # Persistence: Save assistant response
                    if conversation_id:
                        try:
                            store.add_message(conversation_id, "assistant", result)
                        except Exception as e:
                            logger.warning("[%s] Failed to save assistant message: %s", conn_id, e)

                    await ws_manager.send_json(conn_id, {
                        "type": "token",
                        "content": result,
                        "metadata": {"task_id": task_id, "mode": mode, "conversation_id": conversation_id}
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

            # Track task per-connection for proper cleanup
            task = asyncio.create_task(handle_request())
            conn_tasks.add(task)
            task.add_done_callback(conn_tasks.discard)

    except WebSocketDisconnect:
        logger.info("[%s] Client disconnected", conn_id)
    except Exception as e:
        logger.error("[%s] Fatal error: %s", conn_id, e, exc_info=True)
    finally:
        # SECURITY FIX: Cancel only this connection's tasks, not all connections
        for task in list(conn_tasks):
            try:
                task.cancel()
            except Exception:
                pass
        await ws_manager.disconnect(conn_id)
        logger.info("[%s] Connection cleanup complete", conn_id)
