"""Simple event bus for decoupled communication between components."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

EventHandler = Callable[[dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event: str, handler: EventHandler) -> None:
        self._handlers[event].append(handler)

    def unsubscribe(self, event: str, handler: EventHandler) -> None:
        if event in self._handlers:
            self._handlers[event] = [h for h in self._handlers[event] if h is not handler]

    def emit(self, event: str, data: dict[str, Any] | None = None) -> None:
        for handler in self._handlers.get(event, []):
            handler(data or {})
