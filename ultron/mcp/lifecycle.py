"""MCP stdio sunucularının asenkron yaşam döngüsü (başlat / durdur)."""

from __future__ import annotations

import logging
import shutil
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Optional

from ultron.mcp.schemas import MCPSettings

if TYPE_CHECKING:
    from mcp import ClientSession

logger = logging.getLogger(__name__)


class MCPClusterManager:
    """Birden fazla MCP sunucusunu AsyncExitStack ile yönetir."""

    def __init__(self, settings: MCPSettings, config_path: Optional[Path] = None) -> None:
        self._settings = settings
        self._config_path = config_path
        self._stack: Optional[AsyncExitStack] = None
        self._sessions: dict[str, "ClientSession"] = {}
        self._started = False
        self._errors: dict[str, str] = {}
        self._sampling_handler: Optional[callable] = None

    def set_sampling_handler(self, handler: callable) -> None:
        """Set a global sampling handler for all MCP sessions."""
        self._sampling_handler = handler

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
                
                # Attach sampling handler if provided
                if self._sampling_handler:
                    from mcp.types import CreateMessageRequest
                    
                    async def _wrap_sampling(request: CreateMessageRequest):
                        # Extract prompt from messages
                        prompt = "\n".join([m.content.text for m in request.messages if hasattr(m.content, "text")])
                        return await self._sampling_handler(srv.id, prompt, request.maxTokens or 1000)
                    
                    session.set_request_handler(CreateMessageRequest, _wrap_sampling)

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

    async def add_server(self, server_def: MCPServerDefinition) -> bool:
        """Add, start, and persist a new MCP server at runtime."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        import os as _os

        # Avoid duplicates
        if any(s.id == server_def.id for s in self._settings.servers):
            logger.warning("MCP server with ID '%s' already exists", server_def.id)
            return False

        try:
            # 1. Try to start it
            if self._stack is None:
                self._stack = AsyncExitStack()

            env_merged = {str(k): str(v) for k, v in _os.environ.items()}
            env_merged.update(server_def.env)

            params = StdioServerParameters(
                command=server_def.command,
                args=list(server_def.args),
                env=env_merged,
                cwd=server_def.cwd,
            )
            
            read_write = await self._stack.enter_async_context(stdio_client(params))
            read, write = read_write
            session = await self._stack.enter_async_context(ClientSession(read, write))
            
            # Attach sampling handler if provided
            if self._sampling_handler:
                from mcp.types import CreateMessageRequest
                
                async def _wrap_sampling(request: CreateMessageRequest):
                    prompt = "\n".join([m.content.text for m in request.messages if hasattr(m.content, "text")])
                    return await self._sampling_handler(server_def.id, prompt, request.maxTokens or 1000)
                
                session.set_request_handler(CreateMessageRequest, _wrap_sampling)

            await session.initialize()
            
            self._sessions[server_def.id] = session
            self._settings.servers.append(server_def)
            
            # 2. Persist to file
            self.persist_to_file()
            
            logger.info("Dinamik MCP sunucu eklendi ve başlatıldı: %s", server_def.id)
            return True
        except Exception as e:
            logger.error("Dinamik MCP sunucu eklenemedi [%s]: %s", server_def.id, e)
            return False

    def persist_to_file(self) -> None:
        """Save current MCP settings back to YAML."""
        if not self._config_path:
            return
            
        import yaml
        try:
            # We want to save under the 'mcp' key if that's how it's structured
            data = {"mcp": self._settings.model_dump(exclude_none=True)}
            self._config_path.write_text(
                yaml.dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8"
            )
            logger.info("MCP ayarları '%s' dosyasına kaydedildi", self._config_path)
        except Exception as e:
            logger.error("MCP ayarları kaydedilemedi: %s", e)
