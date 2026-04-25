"""Enhanced Async Event Bus for Ultron v3.0."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional, Dict, List

logger = logging.getLogger("ultron.event_bus")

@dataclass
class Event:
    """An event on the bus."""
    name: str
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization (e.g. WebSocket)."""
        return {
            "name": self.name,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }

Handler = Callable[[Event], Coroutine[None, None, None]]

class EventBus:
    """Pub/sub event bus for Ultron AGI communication."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Handler]] = defaultdict(list)
        self._global_handlers: List[Handler] = []
        self._event_log: List[Event] = []
        self._max_log = 1000  # Keep last 1000 events
        self._ws_bridge: Optional[Callable[[Dict[str, Any]], Coroutine[None, None, None]]] = None

    def subscribe(self, event_name: str, handler: Handler) -> None:
        """Subscribe to a specific event type."""
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)
            logger.debug(f"Subscribed to '{event_name}': {handler.__name__}")

    def subscribe_all(self, handler: Handler) -> None:
        """Subscribe to ALL events."""
        if handler not in self._global_handlers:
            self._global_handlers.append(handler)

    def set_ws_bridge(self, bridge_func: Callable[[Dict[str, Any]], Coroutine[None, None, None]]):
        """Set a bridge function to forward events to a WebSocket (frontend)."""
        self._ws_bridge = bridge_func
        logger.info("WebSocket bridge connected to EventBus.")

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers and the WebSocket bridge."""
        # 1. Append to log
        self._event_log.append(event)
        if len(self._event_log) > self._max_log:
            self._event_log = self._event_log[-self._max_log:]

        # 2. Fire WebSocket bridge
        if self._ws_bridge:
            asyncio.create_task(self._ws_bridge(event.to_dict()))

        # 3. Collect handlers
        handlers = self._handlers.get(event.name, [])
        tasks = []
        
        for handler in handlers:
            tasks.append(self._safe_call(handler, event))

        for handler in self._global_handlers:
            tasks.append(self._safe_call(handler, event))

        # 4. Execute all handlers in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Event handler error [{event.name}]: {result}")

        logger.debug(f"Published event '{event.name}' from '{event.source}'")

    async def publish_simple(self, name: str, source: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Convenience: publish without creating Event object."""
        await self.publish(Event(name=name, source=source, data=data or {}))

    @staticmethod
    async def _safe_call(handler: Handler, event: Event) -> None:
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Handler {handler.__name__} failed on event {event.name}: {e}")
            raise

    def get_history(self, count: int = 100, event_name: Optional[str] = None) -> List[Event]:
        """Get event history, optionally filtered."""
        events = self._event_log
        if event_name:
            events = [e for e in events if e.name == event_name]
        return events[-count:]

    def clear(self) -> None:
        """Clear all handlers and event log."""
        self._handlers.clear()
        self._global_handlers.clear()
        self._event_log.clear()

# Global event bus instance
event_bus = EventBus()
