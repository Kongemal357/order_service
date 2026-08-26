from abc import ABC, abstractmethod

from .repositories import OrderRepository


class UnitOfWork(ABC):
    """Port for Unit of Work pattern - manages transactions."""

    order_repo: OrderRepository

    @abstractmethod
    async def __aenter__(self):
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    async def commit(self):
        pass

    @abstractmethod
    async def rollback(self):
        pass
