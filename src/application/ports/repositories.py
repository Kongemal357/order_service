from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.domain.models import Order


class OrderRepository(ABC):
    """Port for order repository operations."""

    @abstractmethod
    async def save(self, order: Order) -> Order:
        pass

    @abstractmethod
    async def get_by_id(self, order_id: UUID) -> Optional[Order]:
        pass

    @abstractmethod
    async def get_by_idempotency_key(self, key: str) -> Optional[Order]:
        pass

    @abstractmethod
    async def update(self, order: Order) -> Order:
        pass
