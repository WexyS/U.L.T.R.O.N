"""MCP araçlarını OpenAI function şemasına çevirme ve call_tool yönlendirme."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from ultron.v2.mcp.lifecycle import MCPClusterManager
from ultron.v2.core.security import SecurityManager

logger = logging.getLogger(__name__)

_SAFE = re.compile(r"[^a-zA-Z0-9_-]+")


def _openai_fn_name(server_id: str, tool_name: str) -> str:
    raw = f"ultronmcp_{server_id}_{tool_name}"
    s = _SAFE.sub("_", raw)
    return s[:120]


class MCPBridge:
    """MCP oturumları ↔ OpenAI tools ↔ MCP call_tool."""

    def __init__(self, manager: MCPClusterManager, security: Optional[SecurityManager] = None) -> None:
        self._manager = manager
        self._security = security
        # openai_name -> (server_id, mcp_tool_name)
        self._name_map: dict[str, tuple[str, str]] = {}
        # openai_name -> OpenAI tool dict (cached)
        self._tool_defs: list[dict[str, Any]] = []
        # Optional policy gates (env-driven)
        import os
        allowed = (os.getenv("ULTRON_MCP_ALLOWED_SERVERS", "") or "").strip()
        self._allowed_servers: Optional[set[str]] = (
            {x.strip() for x in allowed.split(",") if x.strip()} if allowed else None
        )
        self._sampling_callback: Optional[callable] = None

    def set_sampling_callback(self, callback: callable) -> None:
        """Set a callback for LLM sampling requests from MCP servers."""
        self._sampling_callback = callback

    def has_tools(self) -> bool:
        return bool(self._tool_defs)

    async def refresh_tool_catalog(self) -> None:
        """Bağlı MCP sunucularından list_tools ile katalog oluştur."""
        self._name_map.clear()
        self._tool_defs.clear()

        for sid in self._manager.list_server_ids():
            session = self._manager.get_session(sid)
            if session is None:
                continue
            try:
                listed = await session.list_tools()
            except Exception as e:
                logger.warning("list_tools başarısız [%s]: %s", sid, e)
                continue

            used: set[str] = set()
            for t in getattr(listed, "tools", []) or []:
                mcp_name = getattr(t, "name", "") or ""
                if not mcp_name:
                    continue
                fname = _openai_fn_name(sid, mcp_name)
                while fname in used:
                    fname = _openai_fn_name(sid, mcp_name + "_x")
                used.add(fname)
                self._name_map[fname] = (sid, mcp_name)

                desc = (getattr(t, "description", None) or f"MCP {sid} — {mcp_name}")[:2000]
                schema = getattr(t, "inputSchema", None)
                params: dict[str, Any]
                if schema is not None and hasattr(schema, "model_dump"):
                    try:
                        params = schema.model_dump(exclude_none=True)
                    except Exception:
                        params = {"type": "object", "additionalProperties": True}
                elif isinstance(schema, dict):
                    params = schema
                else:
                    params = {"type": "object", "additionalProperties": True}

                self._tool_defs.append(
                    {
                        "type": "function",
                        "function": {
                            "name": fname,
                            "description": desc,
                            "parameters": params,
                        },
                    }
                )

        logger.info("MCP araç kataloğu: %d function", len(self._tool_defs))

    def openai_tools(self) -> list[dict[str, Any]]:
        return list(self._tool_defs)

    async def invoke_openai_function(self, name: str, arguments: Any) -> str:
        """LLM function çağrısını MCP'ye ilet."""
        pair = self._name_map.get(name)
        if not pair:
            return f"Bilinmeyen MCP aracı: {name}"
        sid, mcp_tool = pair
        if self._allowed_servers is not None and sid not in self._allowed_servers:
            return f"🔒 MCP güvenlik: sunucu izinli değil: {sid}"
        session = self._manager.get_session(sid)
        if session is None:
            return f"MCP oturumu yok: {sid}"

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}

        # SECURITY: best-effort path allowlist enforcement for filesystem-like tools.
        # Many MCP filesystem servers use keys like: path, file_path, directory, root, target, src, dst
        if self._security is not None:
            for k in ("path", "file_path", "filepath", "directory", "dir", "root", "target", "src", "dst"):
                v = arguments.get(k)
                if isinstance(v, str) and v.strip():
                    if not self._security.is_path_allowed(v):
                        return f"🔒 MCP güvenlik: path bloklandı (allowed roots dışında): {v}"

        try:
            result = await session.call_tool(mcp_tool, arguments or None)
        except Exception as e:
            logger.exception("call_tool [%s].%s", sid, mcp_tool)
            return f"MCP hata: {e}"

        chunks: list[str] = []
        for block in getattr(result, "content", []) or []:
            tx = getattr(block, "text", None)
            if tx is not None:
                chunks.append(tx)
            else:
                chunks.append(str(block))
        text = "\n".join(chunks) if chunks else str(result)
        if getattr(result, "isError", False):
            return f"MCP isError: {text}"
        return text

    async def handle_sampling_request(self, server_id: str, prompt: str, max_tokens: int = 1000) -> str:
        """Handle an LLM sampling request from an MCP server."""
        if not self._sampling_callback:
            return "Sampling callback not configured."
        
        logger.info("MCP Sampling request from [%s]: %s", server_id, prompt[:100])
        try:
            return await self._sampling_callback(prompt, max_tokens)
        except Exception as e:
            logger.error("Sampling failed: %s", e)
            return f"Error during sampling: {str(e)}"
