"""Jarvis v2 — Master Workspace + Agentic RAG system."""

__all__ = [
    "CloneRequest",
    "GenerateRequest",
    "SynthesizeRequest",
    "WorkspaceItem",
    "WorkspaceManager",
]


def __getattr__(name: str):
    if name == "WorkspaceManager":
        from .workspace_manager import WorkspaceManager as _WM
        return _WM
    # For models, import directly from .models
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
