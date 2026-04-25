"""MCP yapılandırma ve köprü birim testleri (stdio sunucusu başlatılmaz)."""

from __future__ import annotations

from pathlib import Path

from ultron.mcp.bridge import MCPBridge
from ultron.mcp.lifecycle import MCPClusterManager
from ultron.mcp.loader import load_mcp_settings
from ultron.mcp.schemas import MCPSettings


def test_load_mcp_settings_missing_file(tmp_path: Path) -> None:
    cfg = load_mcp_settings(config_path=tmp_path / "nope.yaml", workspace_dir=str(tmp_path))
    assert cfg.enabled is False
    assert cfg.servers == []


def test_load_mcp_settings_minimal(tmp_path: Path) -> None:
    p = tmp_path / "mcp.yaml"
    p.write_text(
        "mcp:\n  enabled: true\n  servers: []\n",
        encoding="utf-8",
    )
    cfg = load_mcp_settings(config_path=p, workspace_dir=str(tmp_path))
    assert cfg.enabled is True
    assert cfg.servers == []


def test_mcp_bridge_invoke_unknown() -> None:
    import asyncio

    mgr = MCPClusterManager(MCPSettings(enabled=False, servers=[]))
    bridge = MCPBridge(mgr)
    assert bridge.has_tools() is False

    async def _run() -> str:
        return await bridge.invoke_openai_function("missing_tool", {})

    out = asyncio.run(_run())
    assert "Bilinmeyen" in out


def test_openai_tool_name_sanitize() -> None:
    from ultron.mcp import bridge as b

    n = b._openai_fn_name("fs", "read_file")
    assert n.startswith("ultronmcp_")
    assert "read_file" in n
