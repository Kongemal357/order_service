import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.inbox_repository import InboxRepository
from src.application.ports.outbox_repository import OutboxRepository
from src.application.ports.repositories import OrderRepository
from src.domain.models import InboxRecord, Order, OrderStatus, OutboxEvent, OutboxStatus
from src.infrastructure.persistence.models import InboxModel, OrderModel, OutboxModel

logger = logging.getLogger(__name__)


class SQLAlchemyOrderRepository(OrderRepository):
    """SQLAlchemy implementation of OrderRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, order: Order) -> Order:
        logger.debug(f"Saving order: {order.id}")

        model = OrderModel(
            id=order.id,
            user_id=order.user_id,
            item_id=order.item_id,
            quantity=order.quantity,
            status=order.status.value,
            idempotency_key=order.idempotency_key,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

        self.session.add(model)
        await self.session.flush()

        return order

    async def get_by_id(self, order_id: UUID) -> Optional[Order]:
        logger.debug(f"Fetching order by ID: {order_id}")

        stmt = select(OrderModel).where(OrderModel.id == order_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return self._to_domain(model)
        return None

    async def get_by_idempotency_key(self, key: str) -> Optional[Order]:
        logger.debug(f"Fetching order by idempotency key: {key}")

        stmt = select(OrderModel).where(OrderModel.idempotency_key == key)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return self._to_domain(model)
        return None

    async def update(self, order: Order) -> Order:
        logger.debug(f"Updating order: {order.id}")

        stmt = select(OrderModel).where(OrderModel.id == order.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            model.status = order.status.value
            model.payment_id = order.payment_id
            model.updated_at = order.updated_at
            await self.session.flush()

        return order

    def _to_domain(self, model: OrderModel) -> Order:
        return Order(
            id=model.id,
            user_id=model.user_id,
            item_id=model.item_id,
            quantity=model.quantity,
            status=OrderStatus(model.status),
            payment_id=model.payment_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            idempotency_key=model.idempotency_key,
        )

    def _to_orm(self, order: Order) -> OrderModel:
        return OrderModel(
            id=order.id,
            user_id=order.user_id,
            item_id=order.item_id,
            quantity=order.quantity,
            status=order.status.value,
            payment_id=order.payment_id,
            idempotency_key=order.idempotency_key,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )


class SQLAlchemyOutboxRepository(OutboxRepository):
    """SQLAlchemy implementation of OutboxRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, event: OutboxEvent) -> OutboxEvent:
        model = OutboxModel(
            id=event.id,
            event_type=event.event_type,
            payload=event.payload,
            idempotency_key=event.idempotency_key,
            status=event.status.value,
            created_at=event.created_at,
            sent_at=event.sent_at,
        )
        self.session.add(model)
        await self.session.flush()
        return event

    async def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        stmt = (
            select(OutboxModel)
            .where(OutboxModel.status == OutboxStatus.PENDING)
            .order_by(OutboxModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self._to_domain(m) for m in models]

    async def mark_sent(self, event_id: UUID) -> None:
        stmt = (
            update(OutboxModel)
            .where(OutboxModel.id == event_id)
            .values(
                status=OutboxStatus.SENT, sent_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def mark_failed(self, event_id: UUID) -> None:
        stmt = (
            update(OutboxModel).where(OutboxModel.id == event_id).values(status=OutboxStatus.FAILED)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    @staticmethod
    def _to_domain(model: OutboxModel) -> OutboxEvent:
        return OutboxEvent(
            id=model.id,
            event_type=model.event_type,
            payload=model.payload,
            idempotency_key=model.idempotency_key,
            status=OutboxStatus(model.status),
            created_at=model.created_at,
            sent_at=model.sent_at,
        )


class SQLAlchemyInboxRepository(InboxRepository):
    """SQLAlchemy implementation of InboxRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, record: InboxRecord) -> InboxRecord:
        model = InboxModel(
            id=record.id,
            event_id=record.event_id,
            idempotency_key=record.idempotency_key,
            event_type=record.event_type,
            processed_at=record.processed_at,
        )
        self.session.add(model)
        await self.session.flush()
        return record

    async def get_by_idempotency_key(self, key: str) -> Optional[InboxRecord]:
        stmt = select(InboxModel).where(InboxModel.idempotency_key == key)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return InboxRecord(
                id=model.id,
                event_id=model.event_id,
                idempotency_key=model.idempotency_key,
                event_type=model.event_type,
                processed_at=model.processed_at,
            )
        return None
