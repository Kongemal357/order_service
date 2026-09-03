from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from src.domain.models import OutboxEvent


class OutboxRepository(ABC):
    """Port for outbox repository operations."""

    @abstractmethod
    async def save(self, event: OutboxEvent) -> OutboxEvent:
        pass

    @abstractmethod
    async def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        pass

    @abstractmethod
    async def mark_sent(self, event_id: UUID) -> None:
        pass

    @abstractmethod
    async def mark_failed(self, event_id: UUID) -> None:
        pass
