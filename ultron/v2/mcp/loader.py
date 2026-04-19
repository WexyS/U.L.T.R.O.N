"""MCP YAML yükleme ve yer tutucu çözümleme."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from ultron.v2.mcp.schemas import MCPSettings, MCPServerDefinition

logger = logging.getLogger(__name__)


def _substitute(s: str, workspace: str, project_root: str) -> str:
    return (
        s.replace("{{WORKSPACE}}", workspace)
        .replace("{{PROJECT_ROOT}}", project_root)
    )


def _expand_server(
    srv: MCPServerDefinition,
    workspace: str,
    project_root: str,
) -> MCPServerDefinition:
    args = [_substitute(a, workspace, project_root) for a in srv.args]
    cwd = _substitute(srv.cwd, workspace, project_root) if srv.cwd else None
    env = {k: _substitute(v, workspace, project_root) for k, v in srv.env.items()}
    return srv.model_copy(update={"args": args, "cwd": cwd, "env": env})


def load_mcp_settings(
    *,
    config_path: Optional[Path] = None,
    workspace_dir: str = "./workspace",
    project_root: Optional[Path] = None,
) -> MCPSettings:
    """mcp.yaml yükle; yoksa veya hatalıysa kapalı MCPSettings döner."""
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent.parent

    path = config_path
    if path is None:
        env_p = (os.environ.get("ULTRON_MCP_CONFIG") or "").strip()
        if env_p:
            path = Path(env_p).expanduser()
        else:
            path = project_root / "config" / "mcp.yaml"

    ws = str(Path(workspace_dir).expanduser().resolve())
    pr = str(project_root.resolve())

    if not path.is_file():
        logger.debug("MCP config not found: %s (MCP disabled)", path)
        return MCPSettings(enabled=False, servers=[])

    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        logger.warning("MCP config parse failed %s: %s", path, e)
        return MCPSettings(enabled=False, servers=[])

    if raw is None:
        return MCPSettings(enabled=False, servers=[])

    block = raw.get("mcp", raw) if isinstance(raw, dict) else {}
    if not isinstance(block, dict):
        return MCPSettings(enabled=False, servers=[])

    try:
        settings = MCPSettings.model_validate(block)
    except Exception as e:
        logger.warning("MCP settings validation failed: %s", e)
        return MCPSettings(enabled=False, servers=[])

    expanded = [_expand_server(s, ws, pr) for s in settings.servers]
    return settings.model_copy(update={"servers": expanded})
