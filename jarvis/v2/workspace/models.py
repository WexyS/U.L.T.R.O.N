"""Pydantic schemas for Workspace operations."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CloneRequest(BaseModel):
    """Request to clone a website into the workspace."""

    url: str = Field(..., description="URL of the website to clone")
    site_name: Optional[str] = Field(None, description="Friendly name; derived from domain if omitted")
    extract_components: bool = Field(True, description="Whether to detect UI components")


class GenerateRequest(BaseModel):
    """Request to generate an application from an idea."""

    idea: str = Field(..., description="Description of the app to generate")
    project_name: Optional[str] = Field(None, description="Project folder name; auto-generated if omitted")
    use_template: Optional[str] = Field(None, description="Name of a cloned template to use as inspiration")
    tech_stack: str = Field("html-css-js", description="Target stack: html-css-js, react, vue, fastapi")


class SynthesizeRequest(BaseModel):
    """Request to synthesize from multiple templates via RAG."""

    user_command: str = Field(..., description="Natural-language synthesis command")
    source_templates: Optional[List[str]] = Field(
        None, description="Template names to use; auto-selected via ChromaDB if empty"
    )
    target_project: str = Field(..., description="Output project folder name")


class WorkspaceItem(BaseModel):
    """Represents a single workspace item (cloned, generated, or synthesized)."""

    id: str
    name: str
    type: str  # "cloned" | "generated" | "synthesized"
    url: Optional[str] = None
    created_at: datetime
    description: str = ""
    components: List[str] = Field(default_factory=list)
    file_path: str
    chroma_id: Optional[str] = None

    def dict(self, *args, **kwargs):  # type: ignore[override]
        d = super().model_dump(*args, **kwargs)
        d["created_at"] = self.created_at.isoformat()
        return d
