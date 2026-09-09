from abc import ABC, abstractmethod
from typing import AsyncContextManager, Protocol

from .inbox_repository import InboxRepository
from .outbox_repository import OutboxRepository
from .repositories import OrderRepository


class UnitOfWork(Protocol):
    """Unit of Work interface - represents a transaction."""

    order_repo: OrderRepository
    outbox_repo: OutboxRepository
    inbox_repo: InboxRepository

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class UnitOfWorkFactory(ABC):
    """Factory interface for creating Unit of Work instances."""

    @abstractmethod
    async def __call__(self) -> AsyncContextManager[UnitOfWork]:
        """Create and return a UnitOfWork context manager."""
        pass
