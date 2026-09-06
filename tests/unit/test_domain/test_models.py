from decimal import Decimal
from uuid import uuid4

import pytest

from src.domain.exceptions import DomainError
from src.domain.models import (
    EventType,
    InboxRecord,
    Money,
    Order,
    OrderStatus,
    OutboxEvent,
    OutboxStatus,
)


class TestMoney:
    def test_money_multiplication(self):
        money = Money(Decimal("100.00"))
        result = money * 3
        assert result.amount == Decimal("300.00")

    def test_money_addition(self):
        m1 = Money(Decimal("100.00"))
        m2 = Money(Decimal("50.00"))
        result = m1 + m2
        assert result.amount == Decimal("150.00")

    def test_money_str(self):
        money = Money(Decimal("100.00"))
        assert str(money) == "100.00"


class TestOrder:
    def test_create_order(self):
        user_id = "user-123"
        item_id = uuid4()
        quantity = 3
        item_price = Decimal("100.00")
        idempotency_key = "test-key"

        order = Order.create(
            user_id=user_id,
            item_id=item_id,
            quantity=quantity,
            item_price=item_price,
            idempotency_key=idempotency_key,
        )

        assert order.user_id == user_id
        assert order.item_id == item_id
        assert order.quantity == quantity
        assert order.status == OrderStatus.NEW
        assert order.idempotency_key == idempotency_key
        assert order.total_amount is not None
        assert order.total_amount.amount == Decimal("300.00")
        assert order.payment_id is None

    def test_create_order_with_idempotency_key(self):
        order = Order.create(
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            item_price=Decimal("100.00"),
            idempotency_key="test-key",
        )
        assert order.idempotency_key == "test-key"

    def test_mark_paid(self):
        order = Order.create(
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            item_price=Decimal("100.00"),
            idempotency_key="test-key",
        )
        old_updated_at = order.updated_at

        order.mark_paid()

        assert order.status == OrderStatus.PAID
        assert order.updated_at > old_updated_at

    def test_mark_paid_from_wrong_status(self):
        order = Order.create(
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            item_price=Decimal("100.00"),
            idempotency_key="test-key",
        )
        order.mark_paid()

        with pytest.raises(DomainError, match="Cannot mark order"):
            order.mark_paid()

    def test_mark_shipped(self):
        order = Order.create(
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            item_price=Decimal("100.00"),
            idempotency_key="test-key",
        )
        order.mark_paid()
        old_updated_at = order.updated_at

        order.mark_shipped()

        assert order.status == OrderStatus.SHIPPED
        assert order.updated_at > old_updated_at

    def test_mark_shipped_without_paid(self):
        order = Order.create(
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            item_price=Decimal("100.00"),
            idempotency_key="test-key",
        )

        with pytest.raises(DomainError, match="Cannot mark order"):
            order.mark_shipped()

    def test_cancel(self):
        order = Order.create(
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            item_price=Decimal("100.00"),
            idempotency_key="test-key",
        )
        old_updated_at = order.updated_at

        order.cancel()

        assert order.status == OrderStatus.CANCELLED
        assert order.updated_at > old_updated_at

    def test_cancel_already_cancelled(self):
        order = Order.create(
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            item_price=Decimal("100.00"),
            idempotency_key="test-key",
        )
        order.cancel()

        with pytest.raises(DomainError, match="already cancelled"):
            order.cancel()

    def test_set_payment_id(self):
        order = Order.create(
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            item_price=Decimal("100.00"),
            idempotency_key="test-key",
        )
        payment_id = uuid4()
        old_updated_at = order.updated_at

        order.set_payment_id(payment_id)

        assert order.payment_id == payment_id
        assert order.updated_at > old_updated_at


class TestOutboxEvent:
    def test_create_outbox_event(self):
        order_id = uuid4()
        event = OutboxEvent.create(
            event_type=EventType.ORDER_PAID,
            payload={"order_id": str(order_id)},
            idempotency_key="test-key",
        )

        assert event.event_type == "order.paid"
        assert event.payload == {"order_id": str(order_id)}
        assert event.idempotency_key == "test-key"
        assert event.status == OutboxStatus.PENDING
        assert event.sent_at is None

    def test_mark_sent(self):
        event = OutboxEvent.create(
            event_type=EventType.ORDER_PAID,
            payload={"order_id": str(uuid4())},
            idempotency_key="test-key",
        )

        event.mark_sent()

        assert event.status == OutboxStatus.SENT
        assert event.sent_at is not None

    def test_mark_failed(self):
        event = OutboxEvent.create(
            event_type=EventType.ORDER_PAID,
            payload={"order_id": str(uuid4())},
            idempotency_key="test-key",
        )

        event.mark_failed()

        assert event.status == OutboxStatus.FAILED


class TestInboxRecord:
    def test_create_inbox_record(self):
        record = InboxRecord.create(
            event_id="event-123",
            idempotency_key="test-key",
            event_type=EventType.ORDER_SHIPPED,
        )

        assert record.event_id == "event-123"
        assert record.idempotency_key == "test-key"
        assert record.event_type == EventType.ORDER_SHIPPED
        assert record.processed_at is not None
