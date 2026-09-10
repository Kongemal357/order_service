from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.application.dto.event_dto import (
    OrderCancelledEventDTO,
    OrderShippedEventDTO,
)
from src.application.usecases.process_shipping_event import ProcessShippingEventUseCase
from src.domain.exceptions import OrderNotFoundError
from src.domain.models import EventType, NotificationType, Order, OrderStatus

pytestmark = pytest.mark.asyncio


@pytest.fixture
def use_case(mock_notification_service):
    return ProcessShippingEventUseCase(notification_service=mock_notification_service)


def make_order(status: OrderStatus) -> Order:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return Order(
        id=uuid4(),
        user_id="user-1",
        item_id=uuid4(),
        quantity=1,
        status=status,
        created_at=now,
        updated_at=now,
        idempotency_key="key-1",
    )


class TestProcessShipped:
    """Tests for ProcessShippingEventUseCase.process_shipped."""

    async def test_ships_order_in_paid_status(self, use_case, mock_uow):
        # Given
        order = make_order(OrderStatus.PAID)
        mock_uow.order_repo.get_by_id.return_value = order
        event_dto = OrderShippedEventDTO(order_id=order.id)

        # When
        result = await use_case.process_shipped(event_dto, mock_uow)

        # Then
        assert result is True
        assert order.status == OrderStatus.SHIPPED
        mock_uow.order_repo.get_by_id.assert_awaited_once_with(order.id)
        mock_uow.order_repo.update.assert_awaited_once_with(order)

    async def test_returns_false_when_order_not_paid(self, use_case, mock_uow):
        # Given
        order = make_order(OrderStatus.NEW)
        mock_uow.order_repo.get_by_id.return_value = order
        event_dto = OrderShippedEventDTO(order_id=order.id)

        # When
        result = await use_case.process_shipped(event_dto, mock_uow)

        # Then
        assert result is False
        assert order.status == OrderStatus.NEW
        mock_uow.order_repo.update.assert_not_awaited()

    async def test_returns_false_when_order_already_shipped(self, use_case, mock_uow):
        # Given
        order = make_order(OrderStatus.SHIPPED)
        mock_uow.order_repo.get_by_id.return_value = order
        event_dto = OrderShippedEventDTO(order_id=order.id)

        # When
        result = await use_case.process_shipped(event_dto, mock_uow)

        # Then
        assert result is False
        mock_uow.order_repo.update.assert_not_awaited()

    async def test_returns_false_when_order_cancelled(self, use_case, mock_uow):
        # Given
        order = make_order(OrderStatus.CANCELLED)
        mock_uow.order_repo.get_by_id.return_value = order
        event_dto = OrderShippedEventDTO(order_id=order.id)

        # When
        result = await use_case.process_shipped(event_dto, mock_uow)

        # Then
        assert result is False
        mock_uow.order_repo.update.assert_not_awaited()

    async def test_raises_when_order_not_found(self, use_case, mock_uow):
        # Given
        mock_uow.order_repo.get_by_id.return_value = None
        event_dto = OrderShippedEventDTO(order_id=uuid4())

        # When / Then
        with pytest.raises(OrderNotFoundError):
            await use_case.process_shipped(event_dto, mock_uow)

        mock_uow.order_repo.update.assert_not_awaited()


class TestProcessCancelled:
    """Tests for ProcessShippingEventUseCase.process_cancelled."""

    async def test_cancels_order_in_paid_status(self, use_case, mock_uow):
        # Given
        order = make_order(OrderStatus.PAID)
        mock_uow.order_repo.get_by_id.return_value = order
        event_dto = OrderCancelledEventDTO(order_id=order.id, reason="stock")

        # When
        result = await use_case.process_cancelled(event_dto, mock_uow)

        # Then
        assert result is True
        assert order.status == OrderStatus.CANCELLED
        mock_uow.order_repo.get_by_id.assert_awaited_once_with(order.id)
        mock_uow.order_repo.update.assert_awaited_once_with(order)

    async def test_cancels_order_in_new_status(self, use_case, mock_uow):
        # Given
        order = make_order(OrderStatus.NEW)
        mock_uow.order_repo.get_by_id.return_value = order
        event_dto = OrderCancelledEventDTO(order_id=order.id, reason="stock")

        # When
        result = await use_case.process_cancelled(event_dto, mock_uow)

        # Then
        assert result is True
        assert order.status == OrderStatus.CANCELLED
        mock_uow.order_repo.update.assert_awaited_once_with(order)

    async def test_returns_false_when_order_already_shipped(self, use_case, mock_uow):
        # Given
        order = make_order(OrderStatus.SHIPPED)
        mock_uow.order_repo.get_by_id.return_value = order
        event_dto = OrderCancelledEventDTO(order_id=order.id, reason="stock")

        # When
        result = await use_case.process_cancelled(event_dto, mock_uow)

        # Then
        assert result is False
        assert order.status == OrderStatus.SHIPPED
        mock_uow.order_repo.update.assert_not_awaited()

    async def test_returns_false_when_order_already_cancelled(self, use_case, mock_uow):
        # Given
        order = make_order(OrderStatus.CANCELLED)
        mock_uow.order_repo.get_by_id.return_value = order
        event_dto = OrderCancelledEventDTO(order_id=order.id, reason="stock")

        # When
        result = await use_case.process_cancelled(event_dto, mock_uow)

        # Then
        assert result is False
        mock_uow.order_repo.update.assert_not_awaited()

    async def test_raises_when_order_not_found(self, use_case, mock_uow):
        # Given
        mock_uow.order_repo.get_by_id.return_value = None
        event_dto = OrderCancelledEventDTO(order_id=uuid4(), reason="stock")

        # When / Then
        with pytest.raises(OrderNotFoundError):
            await use_case.process_cancelled(event_dto, mock_uow)

        mock_uow.order_repo.update.assert_not_awaited()


# ---------- send_notifications ----------


class TestSendNotifications:
    """Tests for ProcessShippingEventUseCase.send_notifications."""

    async def test_sends_shipped_notification(self, use_case, mock_notification_service):
        # Given
        order_id = uuid4()

        # When
        await use_case.send_notifications(order_id, EventType.ORDER_SHIPPED)

        # Then
        mock_notification_service.send_notification.assert_awaited_once_with(
            order_id,
            NotificationType.ORDER_SHIPPED,
        )

    async def test_sends_cancelled_notification(self, use_case, mock_notification_service):
        # Given
        order_id = uuid4()

        # When
        await use_case.send_notifications(order_id, EventType.ORDER_CANCELLED)

        # Then
        mock_notification_service.send_notification.assert_awaited_once_with(
            order_id,
            NotificationType.ORDER_CANCELLED,
        )

    async def test_does_not_send_for_other_event_types(self, use_case, mock_notification_service):
        # Given
        order_id = uuid4()

        # When
        await use_case.send_notifications(order_id, EventType.ORDER_PAID)

        # Then
        mock_notification_service.send_notification.assert_not_awaited()

    async def test_propagates_notification_error(self, use_case, mock_notification_service):
        # Given
        order_id = uuid4()
        mock_notification_service.send_notification.side_effect = RuntimeError(
            "notification failed"
        )

        # When / Then
        with pytest.raises(RuntimeError, match="notification failed"):
            await use_case.send_notifications(order_id, EventType.ORDER_SHIPPED)
