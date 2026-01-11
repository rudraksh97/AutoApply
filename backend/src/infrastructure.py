"""
Infrastructure implementations for core system interfaces.
"""

import asyncio
import logging
from typing import Any, Set
from src.interfaces import EventPublisher, Deduplicator

class InMemoryDeduplicator(Deduplicator):
    """
    Simple in-memory implementation of the Deduplicator.
    NOTE: This is not persistent across restarts.
    """
    def __init__(self):
        self._seen_keys: Set[str] = set()

    def is_new(self, key: str) -> bool:
        return key not in self._seen_keys

    def mark_seen(self, key: str) -> None:
        self._seen_keys.add(key)

class LoggingEventPublisher(EventPublisher):
    """
    Simple event publisher that logs events.
    Useful for local development and debugging.
    """
    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        logging.info(f"Event Published: {event_type} | Data: {data}")
        # In a real scenario, this might push to a queue (Redis, RabbitMQ)
        # or trigger a background task.

class AsyncCallbackPublisher(EventPublisher):
    """
    Dispatched events to an async callback function.
    Useful for decoupling without a full message broker.
    """
    def __init__(self, callback):
        self.callback = callback

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        # Fire and forget if callback is handled in background
        asyncio.create_task(self.callback(event_type, data))
