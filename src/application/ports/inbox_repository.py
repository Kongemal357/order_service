from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.domain.models import InboxRecord


class InboxRepository(ABC):
    """Port for inbox repository operations."""

    @abstractmethod
    async def save(self, record: InboxRecord) -> InboxRecord | None:
        pass

    @abstractmethod
    async def get_by_event_id(self, event_id: str) -> Optional[InboxRecord]:
        pass

    @abstractmethod
    async def get_pending(self, limit: int = 100) -> List[InboxRecord]:
        pass

    @abstractmethod
    async def mark_processed(self, record_id: UUID) -> None:
        pass

    @abstractmethod
    async def exists(self, event_id: str) -> bool:
        pass
