"""
Inbox repository port.
"""

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.models import InboxRecord


class InboxRepository(ABC):
    """Port for inbox repository operations."""

    @abstractmethod
    async def save(self, record: InboxRecord) -> InboxRecord:
        pass

    @abstractmethod
    async def get_by_idempotency_key(self, key: str) -> Optional[InboxRecord]:
        pass
