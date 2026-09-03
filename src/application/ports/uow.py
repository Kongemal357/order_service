from abc import ABC, abstractmethod
from typing import AsyncContextManager, Protocol

from .inbox_repository import InboxRepository
from .outbox_repository import OutboxRepository
from .repositories import OrderRepository


class UnitOfWork(ABC):
    @abstractmethod
    async def __call__(self) -> AsyncContextManager:
        pass


class UnitOfWorkImpl(Protocol):
    order_repo: OrderRepository
    outbox_repo: OutboxRepository
    inbox_repo: InboxRepository

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
