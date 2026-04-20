"""Composer API routes — multi-file code generation & editing."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2/composer", tags=["composer"])


# ── Request/Response Models ──────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    workspace: str = ""
    context_files: list[str] = []


class ApplyRequest(BaseModel):
    session_id: str


class RollbackRequest(BaseModel):
    session_id: str


# ── Helper ───────────────────────────────────────────────────────────────

def _get_composer():
    """Get composer agent from orchestrator."""
    try:
        from ultron.api.main import _orchestrator
        if _orchestrator and hasattr(_orchestrator, '_composer'):
            return _orchestrator._composer
    except Exception:
        pass

    # Create a standalone composer
    from ultron.v2.agents.composer_agent import ComposerAgent
    return ComposerAgent(workspace_dir="./workspace")


_standalone_composer = None


def _ensure_composer():
    global _standalone_composer
    composer = _get_composer()
    if composer:
        return composer
    if _standalone_composer is None:
        from ultron.v2.agents.composer_agent import ComposerAgent
        _standalone_composer = ComposerAgent(workspace_dir="./workspace")
    return _standalone_composer


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_changes(request: GenerateRequest):
    """Generate code changes from a natural language prompt."""
    try:
        composer = _ensure_composer()

        # Ensure LLM router is available
        if not composer.llm_router:
            try:
                from ultron.api.main import _orchestrator
                if _orchestrator:
                    composer.llm_router = _orchestrator.llm_router
            except Exception:
                pass

        if not composer.llm_router:
            raise HTTPException(
                status_code=503,
                detail="LLM router not available. Ensure the backend is fully initialized."
            )

        session = await composer.generate(
            prompt=request.prompt,
            workspace=request.workspace,
            context_files=request.context_files,
        )

        # Build response with diffs
        changes_with_diffs = []
        for change in session.changes:
            changes_with_diffs.append({
                **change.to_dict(),
                "diff": change.diff(),
            })

        return {
            "session_id": session.session_id,
            "prompt": session.prompt,
            "workspace": session.workspace,
            "changes": changes_with_diffs,
            "status": session.status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Composer generate failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply")
async def apply_changes(request: ApplyRequest):
    """Apply generated changes to the workspace."""
    try:
        composer = _ensure_composer()
        result = await composer.apply_changes(request.session_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Composer apply failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback")
async def rollback_changes(request: RollbackRequest):
    """Rollback previously applied changes."""
    try:
        composer = _ensure_composer()
        result = await composer.rollback(request.session_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Composer rollback failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions():
    """List all composer sessions."""
    try:
        composer = _ensure_composer()
        return {"sessions": composer.list_sessions()}
    except Exception as e:
        logger.error("Composer list sessions failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific composer session."""
    try:
        composer = _ensure_composer()
        session = composer.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Composer get session failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context")
async def get_context(workspace: str = "", files: Optional[str] = None):
    """Get workspace context (file tree + key files)."""
    try:
        composer = _ensure_composer()
        context_files = files.split(",") if files else None
        context = composer.get_workspace_context(workspace, context_files)
        return {"context": context, "workspace": workspace or str(composer.workspace_dir)}
    except Exception as e:
        logger.error("Composer context failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
