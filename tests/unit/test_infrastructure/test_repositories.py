from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.domain.models import (
    EventType,
    InboxRecord,
    Order,
    OrderStatus,
    OutboxEvent,
    OutboxStatus,
)
from src.infrastructure.persistence.models import InboxModel, OrderModel, OutboxModel
from src.infrastructure.persistence.repositories import (
    SQLAlchemyInboxRepository,
    SQLAlchemyOrderRepository,
    SQLAlchemyOutboxRepository,
)

pytestmark = pytest.mark.asyncio


class TestSQLAlchemyOrderRepository:
    """Tests for SQLAlchemyOrderRepository."""

    def test_to_domain(self):
        # Given
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order_id = uuid4()
        model = OrderModel(
            id=order_id,
            user_id="user-123",
            item_id=uuid4(),
            quantity=2,
            status=OrderStatus.NEW.value,
            payment_id=uuid4(),
            idempotency_key="test-key",
            created_at=now,
            updated_at=now,
        )
        session = Mock()
        repo = SQLAlchemyOrderRepository(session)

        # When
        domain = repo._to_domain(model)

        # Then
        assert domain.id == model.id
        assert domain.user_id == model.user_id
        assert domain.item_id == model.item_id
        assert domain.quantity == model.quantity
        assert domain.status == OrderStatus.NEW
        assert domain.payment_id == model.payment_id
        assert domain.idempotency_key == model.idempotency_key
        assert domain.created_at == model.created_at
        assert domain.updated_at == model.updated_at

    def test_to_orm(self):
        # Given
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = Order(
            id=uuid4(),
            user_id="user-123",
            item_id=uuid4(),
            quantity=2,
            status=OrderStatus.NEW,
            payment_id=uuid4(),
            created_at=now,
            updated_at=now,
            idempotency_key="test-key",
        )
        session = Mock()
        repo = SQLAlchemyOrderRepository(session)

        # When
        model = repo._to_orm(order)

        # Then
        assert model.id == order.id
        assert model.user_id == order.user_id
        assert model.item_id == order.item_id
        assert model.quantity == order.quantity
        assert model.status == order.status.value
        assert model.payment_id == order.payment_id
        assert model.idempotency_key == order.idempotency_key

    async def test_save(self):
        # Given
        session = Mock()
        session.add = Mock()
        session.flush = AsyncMock()
        repo = SQLAlchemyOrderRepository(session)
        order = Order(
            id=uuid4(),
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            status=OrderStatus.NEW,
            payment_id=None,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            idempotency_key=None,
        )

        # When
        result = await repo.save(order)

        # Then
        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert result == order

    async def test_get_by_id(self):
        # Given
        order_id = uuid4()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        model = OrderModel(
            id=order_id,
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            status=OrderStatus.NEW.value,
            payment_id=None,
            idempotency_key=None,
            created_at=now,
            updated_at=now,
        )
        session = Mock()
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = Mock(return_value=model)
        repo = SQLAlchemyOrderRepository(session)

        # When
        result = await repo.get_by_id(order_id)

        # Then
        session.execute.assert_called_once()
        assert result.id == order_id
        assert result.status == OrderStatus.NEW

    async def test_get_by_id_not_found(self):
        # Given
        order_id = uuid4()
        session = Mock()
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = Mock(return_value=None)
        repo = SQLAlchemyOrderRepository(session)

        # When
        result = await repo.get_by_id(order_id)

        # Then
        assert result is None

    async def test_get_by_idempotency_key(self):
        # Given
        idempotency_key = "test-key"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        model = OrderModel(
            id=uuid4(),
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            status=OrderStatus.NEW.value,
            payment_id=None,
            idempotency_key=idempotency_key,
            created_at=now,
            updated_at=now,
        )
        session = Mock()
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = Mock(return_value=model)
        repo = SQLAlchemyOrderRepository(session)

        # When
        result = await repo.get_by_idempotency_key(idempotency_key)

        # Then
        session.execute.assert_called_once()
        assert result.idempotency_key == idempotency_key
        assert result.status == OrderStatus.NEW

    async def test_update(self):
        # Given
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order_id = uuid4()
        order = Order(
            id=order_id,
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            status=OrderStatus.PAID,
            payment_id=uuid4(),
            created_at=now,
            updated_at=now,
            idempotency_key="test-key",
        )
        model = OrderModel(
            id=order_id,
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            status=OrderStatus.NEW.value,
            payment_id=None,
            idempotency_key="test-key",
            created_at=now,
            updated_at=now,
        )
        session = Mock()
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = Mock(return_value=model)
        session.flush = AsyncMock()
        repo = SQLAlchemyOrderRepository(session)

        # When
        result = await repo.update(order)

        # Then
        session.execute.assert_called_once()
        session.flush.assert_called_once()
        assert model.status == OrderStatus.PAID.value
        assert model.payment_id == order.payment_id
        assert result == order


class TestSQLAlchemyOutboxRepository:
    """Tests for SQLAlchemyOutboxRepository."""

    def test_to_domain(self):
        # Given
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        event_id = uuid4()
        model = OutboxModel(
            id=event_id,
            event_type=EventType.ORDER_PAID.value,
            payload={"order_id": str(uuid4())},
            idempotency_key="test-key",
            status=OutboxStatus.PENDING.value,
            created_at=now,
            sent_at=None,
        )
        session = Mock()
        repo = SQLAlchemyOutboxRepository(session)

        # When
        domain = repo._to_domain(model)

        # Then
        assert domain.id == model.id
        assert domain.event_type == EventType.ORDER_PAID.value
        assert domain.payload == model.payload
        assert domain.idempotency_key == model.idempotency_key
        assert domain.status == OutboxStatus.PENDING
        assert domain.created_at == model.created_at
        assert domain.sent_at is None

    async def test_save(self):
        # Given
        event = OutboxEvent.create(
            event_type=EventType.ORDER_PAID,
            payload={"order_id": str(uuid4())},
            idempotency_key="test-key",
        )
        session = Mock()
        session.add = Mock()
        session.flush = AsyncMock()
        repo = SQLAlchemyOutboxRepository(session)

        # When
        result = await repo.save(event)

        # Then
        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert result == event

    async def test_get_pending(self):
        # Given
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        model = OutboxModel(
            id=uuid4(),
            event_type=EventType.ORDER_PAID.value,
            payload={"order_id": str(uuid4())},
            idempotency_key="test-key",
            status=OutboxStatus.PENDING.value,
            created_at=now,
            sent_at=None,
        )
        session = Mock()
        mock_scalars = AsyncMock()
        mock_scalars.all = Mock(return_value=[model])
        session.scalars = AsyncMock(return_value=mock_scalars)
        repo = SQLAlchemyOutboxRepository(session)

        # When
        result = await repo.get_pending(limit=10)

        # Then
        session.scalars.assert_called_once()
        assert len(result) == 1
        assert result[0].id == model.id
        assert result[0].event_type == EventType.ORDER_PAID.value
        assert result[0].status == OutboxStatus.PENDING

    async def test_get_pending_empty(self):
        # Given
        session = Mock()
        mock_scalars = AsyncMock()
        mock_scalars.all = Mock(return_value=[])
        session.scalars = AsyncMock(return_value=mock_scalars)
        repo = SQLAlchemyOutboxRepository(session)

        # When
        result = await repo.get_pending(limit=10)

        # Then
        assert result == []

    async def test_mark_sent(self):
        # Given
        event_id = uuid4()
        session = Mock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        repo = SQLAlchemyOutboxRepository(session)

        # When
        await repo.mark_sent(event_id)

        # Then
        session.execute.assert_called_once()
        session.flush.assert_called_once()

    async def test_mark_failed(self):
        # Given
        event_id = uuid4()
        session = Mock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        repo = SQLAlchemyOutboxRepository(session)

        # When
        await repo.mark_failed(event_id)

        # Then
        session.execute.assert_called_once()
        session.flush.assert_called_once()


class TestSQLAlchemyInboxRepository:
    """Tests for SQLAlchemyInboxRepository."""

    async def test_save(self):
        # Given
        record = InboxRecord.create(
            event_id="event-123",
            idempotency_key="test-key",
            event_type=EventType.ORDER_SHIPPED,
        )
        session = Mock()
        session.add = Mock()
        session.flush = AsyncMock()
        repo = SQLAlchemyInboxRepository(session)

        # When
        result = await repo.save(record)

        # Then
        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert result == record

    async def test_get_by_idempotency_key(self):
        # Given
        idempotency_key = "test-key"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        model = InboxModel(
            id=uuid4(),
            event_id="event-123",
            idempotency_key=idempotency_key,
            event_type=EventType.ORDER_SHIPPED.value,
            processed_at=now,
        )
        session = Mock()
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = Mock(return_value=model)
        repo = SQLAlchemyInboxRepository(session)

        # When
        result = await repo.get_by_idempotency_key(idempotency_key)

        # Then
        session.execute.assert_called_once()
        assert result.idempotency_key == idempotency_key
        assert result.event_type == EventType.ORDER_SHIPPED.value

    async def test_get_by_idempotency_key_not_found(self):
        # Given
        idempotency_key = "test-key"
        session = Mock()
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = Mock(return_value=None)
        repo = SQLAlchemyInboxRepository(session)

        # When
        result = await repo.get_by_idempotency_key(idempotency_key)

        # Then
        assert result is None
