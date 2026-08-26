import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.repositories import OrderRepository
from src.application.ports.uow import UnitOfWork
from src.infrastructure.persistence.database import AsyncSessionLocal
from src.infrastructure.persistence.repositories import SQLAlchemyOrderRepository

logger = logging.getLogger(__name__)


class SQLAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of Unit of Work."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or AsyncSessionLocal
        self.session: AsyncSession | None = None
        self.order_repo: OrderRepository | None = None

    async def __aenter__(self):
        self.session = self.session_factory()
        self.order_repo = SQLAlchemyOrderRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        await self.session.close()

    async def commit(self):
        if self.session:
            logger.debug("Committing transaction")
            await self.session.commit()

    async def rollback(self):
        if self.session:
            logger.warning("Rolling back transaction")
            await self.session.rollback()