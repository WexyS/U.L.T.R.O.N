"""MCP yapılandırması — Pydantic modelleri."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MCPServerDefinition(BaseModel):
    """Tek bir stdio MCP sunucusu."""

    id: str = Field(..., description="Benzersiz kısa kimlik (ör. fs, sqlite)")
    command: str = Field(..., description="Çalıştırılacak komut (ör. npx, uvx, python)")
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: Optional[str] = None
    disabled: bool = False


class MCPSettings(BaseModel):
    """config/mcp.yaml kökü."""

    enabled: bool = False
    servers: list[MCPServerDefinition] = Field(default_factory=list)
