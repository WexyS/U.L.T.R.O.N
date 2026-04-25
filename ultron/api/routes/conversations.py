"""Conversation API routes — CRUD endpoints for conversation management."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ── Request/Response Models ──────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    title: str = "New Chat"
    model: str = "ollama"
    mode: str = "chat"
    metadata: dict = {}


class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    mode: Optional[str] = None
    metadata: Optional[dict] = None


class AddMessageRequest(BaseModel):
    role: str = "user"
    content: str
    metadata: dict = {}


class SearchRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    limit: int = 20


# ── Helper ───────────────────────────────────────────────────────────────

def _get_store():
    """Get conversation store from app state."""
    from ultron.api.main import get_conversation_store
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        # If called from async context, schedule coroutine
        future = asyncio.ensure_future(get_conversation_store())
        # This won't work in sync context, use a fallback
    except RuntimeError:
        pass

    # Direct import fallback
    from ultron.memory.conversation_store import ConversationStore
    return ConversationStore()


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("")
async def list_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
):
    """List all conversations, ordered by most recent."""
    try:
        from ultron.memory.conversation_store import ConversationStore
        store = ConversationStore()
        conversations = store.list_conversations(limit=limit, offset=offset, search=search)
        return {
            "conversations": [c.to_dict() for c in conversations],
            "total": len(conversations),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error("Failed to list conversations: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_conversation(request: Optional[CreateConversationRequest] = None):
    """Create a new conversation."""
    if request is None:
        request = CreateConversationRequest()
    try:
        from ultron.memory.conversation_store import ConversationStore
        store = ConversationStore()
        conv = store.create_conversation(
            title=request.title,
            model=request.model,
            mode=request.mode,
            metadata=request.metadata,
        )
        return conv.to_dict()
    except Exception as e:
        logger.error("Failed to create conversation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation."""
    try:
        from ultron.memory.conversation_store import ConversationStore
        store = ConversationStore()
        conv = store.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conv.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get conversation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{conversation_id}")
async def update_conversation(conversation_id: str, request: UpdateConversationRequest):
    """Update a conversation's properties."""
    try:
        from ultron.memory.conversation_store import ConversationStore
        store = ConversationStore()
        success = store.update_conversation(
            conversation_id=conversation_id,
            title=request.title,
            model=request.model,
            mode=request.mode,
            metadata=request.metadata,
        )
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update conversation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/all")
async def delete_all_conversations():
    """Delete ALL conversations and their messages."""
    try:
        from ultron.memory.conversation_store import ConversationStore
        store = ConversationStore()
        all_convs = store.list_conversations(limit=9999)
        deleted = 0
        for conv in all_convs:
            try:
                store.delete_conversation(conv.id)
                deleted += 1
            except Exception:
                pass
        return {"status": "cleared", "deleted": deleted}
    except Exception as e:
        logger.error("Failed to clear all conversations: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    try:
        from ultron.memory.conversation_store import ConversationStore
        store = ConversationStore()
        success = store.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete conversation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Message Endpoints ────────────────────────────────────────────────────

@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get messages for a conversation."""
    try:
        from ultron.memory.conversation_store import ConversationStore
        store = ConversationStore()
        messages = store.get_messages(conversation_id, limit=limit, offset=offset)
        return {
            "messages": [m.to_dict() for m in messages],
            "total": len(messages),
            "conversation_id": conversation_id,
        }
    except Exception as e:
        logger.error("Failed to get messages: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/messages")
async def add_message(conversation_id: str, request: AddMessageRequest):
    """Add a message to a conversation."""
    try:
        from ultron.memory.conversation_store import ConversationStore
        store = ConversationStore()

        # Verify conversation exists
        conv = store.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        msg = store.add_message(
            conversation_id=conversation_id,
            role=request.role,
            content=request.content,
            metadata=request.metadata,
        )
        return msg.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add message: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Search ───────────────────────────────────────────────────────────────

@router.post("/search")
async def search_messages(request: SearchRequest):
    """Search messages across conversations."""
    try:
        from ultron.memory.conversation_store import ConversationStore
        store = ConversationStore()
        messages = store.search_messages(
            query=request.query,
            conversation_id=request.conversation_id,
            limit=request.limit,
        )
        return {
            "results": [m.to_dict() for m in messages],
            "total": len(messages),
            "query": request.query,
        }
    except Exception as e:
        logger.error("Failed to search messages: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Export/Import ────────────────────────────────────────────────────────

@router.get("/{conversation_id}/export")
async def export_conversation(conversation_id: str):
    """Export a conversation with all messages."""
    try:
        from ultron.memory.conversation_store import ConversationStore
        store = ConversationStore()
        data = store.export_conversation(conversation_id)
        if not data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export conversation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import")
async def import_conversation(data: dict):
    """Import a conversation from exported JSON."""
    try:
        from ultron.memory.conversation_store import ConversationStore
        store = ConversationStore()
        conv_id = store.import_conversation(data)
        if not conv_id:
            raise HTTPException(status_code=400, detail="Import failed")
        return {"conversation_id": conv_id, "status": "imported"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to import conversation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
