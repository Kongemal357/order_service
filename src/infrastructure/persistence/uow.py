import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.ports.inbox_repository import InboxRepository
from src.application.ports.outbox_repository import OutboxRepository
from src.application.ports.repositories import OrderRepository
from src.infrastructure.persistence.repositories import (
    SQLAlchemyInboxRepository,
    SQLAlchemyOrderRepository,
    SQLAlchemyOutboxRepository,
)

logger = logging.getLogger(__name__)


class _UnitOfWorkImplementation:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._order_repo = SQLAlchemyOrderRepository(session)
        self._outbox_repo = SQLAlchemyOutboxRepository(session)
        self._inbox_repo = SQLAlchemyInboxRepository(session)
        self._committed = False

    @property
    def is_committed(self) -> bool:
        return self._committed

    @property
    def order_repo(self) -> OrderRepository:
        return self._order_repo

    @property
    def outbox_repo(self) -> OutboxRepository:
        return self._outbox_repo

    @property
    def inbox_repo(self) -> InboxRepository:
        return self._inbox_repo

    async def commit(self) -> None:
        await self._session.commit()
        self._committed = True
        logger.debug("Transaction committed")

    async def rollback(self) -> None:
        await self._session.rollback()
        logger.warning("Transaction rolled back")


class SQLAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    @asynccontextmanager
    async def __call__(self) -> AsyncGenerator[_UnitOfWorkImplementation, None]:
        async with self._session_factory() as session:
            uow = _UnitOfWorkImplementation(session)
            try:
                yield uow
                if not uow.is_committed:
                    await session.rollback()
            except Exception:
                await session.rollback()
                raise
