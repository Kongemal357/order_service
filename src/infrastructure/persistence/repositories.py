import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.repositories import OrderRepository
from src.domain.models import Order, OrderStatus
from src.infrastructure.persistence.models import OrderModel

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
