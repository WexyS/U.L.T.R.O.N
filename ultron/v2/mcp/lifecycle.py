"""MCP stdio sunucularının asenkron yaşam döngüsü (başlat / durdur)."""

from __future__ import annotations

import logging
import shutil
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Optional

from ultron.v2.mcp.schemas import MCPSettings

if TYPE_CHECKING:
    from mcp import ClientSession

logger = logging.getLogger(__name__)


class MCPClusterManager:
    """Birden fazla MCP sunucusunu AsyncExitStack ile yönetir."""

    def __init__(self, settings: MCPSettings) -> None:
        self._settings = settings
        self._stack: Optional[AsyncExitStack] = None
        self._sessions: dict[str, "ClientSession"] = {}
        self._started = False
        self._errors: dict[str, str] = {}

    @property
    def enabled(self) -> bool:
        return bool(self._settings.enabled and self._settings.servers)

    @property
    def errors(self) -> dict[str, str]:
        return dict(self._errors)

    async def start(self) -> None:
        if self._started:
            return
        self._errors.clear()
        if not self._settings.enabled:
            logger.info("MCP cluster disabled in config")
            self._started = True
            return

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as e:
            logger.warning("MCP Python SDK yüklü değil (pip install mcp): %s", e)
            self._started = True
            return

        self._stack = AsyncExitStack()
        self._sessions.clear()

        import os as _os

        for srv in self._settings.servers:
            if srv.disabled:
                continue
            cmd0 = srv.command.strip().split()[0] if srv.command.strip() else ""
            if cmd0 and shutil.which(cmd0) is None:
                msg = f"Komut PATH'te yok: {srv.command}"
                logger.warning("MCP sunucu atlandı [%s]: %s", srv.id, msg)
                self._errors[srv.id] = msg
                continue

            try:
                env_merged = {str(k): str(v) for k, v in _os.environ.items()}
                env_merged.update(srv.env)

                params = StdioServerParameters(
                    command=srv.command,
                    args=list(srv.args),
                    env=env_merged,
                    cwd=srv.cwd,
                )
                read_write = await self._stack.enter_async_context(stdio_client(params))
                read, write = read_write
                session = await self._stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                self._sessions[srv.id] = session
                logger.info("MCP sunucu hazır: %s (%s)", srv.id, srv.command)
            except Exception as e:
                logger.exception("MCP sunucu başlatılamadı [%s]", srv.id)
                self._errors[srv.id] = str(e)

        self._started = True

    def get_session(self, server_id: str) -> Optional["ClientSession"]:
        return self._sessions.get(server_id)

    def list_server_ids(self) -> list[str]:
        return list(self._sessions.keys())

    async def stop(self) -> None:
        if self._stack is not None:
            try:
                await self._stack.aclose()
            except Exception as e:
                logger.warning("MCP cluster kapatılırken: %s", e)
        self._stack = None
        self._sessions.clear()
        self._started = False
