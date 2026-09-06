from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.application.usecases.process_shipping_event import ProcessShippingEventUseCase
from src.domain.exceptions import OrderNotFoundError
from src.domain.models import Order, OrderStatus

pytestmark = pytest.mark.asyncio


@pytest.fixture
def order_shipped_event_dto():
    from src.application.dto.event_dto import OrderShippedEventDTO

    return OrderShippedEventDTO(
        order_id=uuid4(),
        item_id=uuid4(),
        quantity=1,
        shipment_id=uuid4(),
        idempotency_key="test-shipped-key",
    )


@pytest.fixture
def order_cancelled_event_dto():
    from src.application.dto.event_dto import OrderCancelledEventDTO

    return OrderCancelledEventDTO(
        order_id=uuid4(),
        item_id=uuid4(),
        quantity=1,
        reason="Test cancellation",
        idempotency_key="test-cancelled-key",
    )


@pytest.fixture
def mock_retry_handler():
    handler = Mock()
    handler.send_to_retry = AsyncMock()
    return handler


class TestProcessShippingEventUseCase:
    async def test_process_shipped_success(
        self,
        order_shipped_event_dto,
        mock_uow_factory,
        mock_retry_handler,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = Order(
            id=order_shipped_event_dto.order_id,
            user_id="user-123",
            item_id=order_shipped_event_dto.item_id,
            quantity=order_shipped_event_dto.quantity,
            status=OrderStatus.PAID,
            payment_id=uuid4(),
            created_at=now,
            updated_at=now,
            idempotency_key=None,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = order

        use_case = ProcessShippingEventUseCase(
            uow_factory=mock_uow_factory,
            retry_handler=mock_retry_handler,
            notification_service=mock_notification_service,
        )

        await use_case.process_shipped(order_shipped_event_dto)

        assert order.status == OrderStatus.SHIPPED
        mock_uow.order_repo.update.assert_called()
        mock_uow.inbox_repo.save.assert_called()
        mock_notification_service.send_notification.assert_called()
        mock_retry_handler.send_to_retry.assert_not_called()

    async def test_process_shipped_order_not_found(
        self,
        order_shipped_event_dto,
        mock_uow_factory,
        mock_retry_handler,
        mock_notification_service,
    ):
        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = None

        use_case = ProcessShippingEventUseCase(
            uow_factory=mock_uow_factory,
            retry_handler=mock_retry_handler,
            notification_service=mock_notification_service,
        )

        with pytest.raises(OrderNotFoundError):
            await use_case.process_shipped(order_shipped_event_dto)

    async def test_process_shipped_already_processed(
        self,
        order_shipped_event_dto,
        mock_uow_factory,
        mock_retry_handler,
        mock_notification_service,
    ):
        mock_uow = mock_uow_factory.return_value
        mock_uow.inbox_repo.get_by_idempotency_key.return_value = Mock()

        use_case = ProcessShippingEventUseCase(
            uow_factory=mock_uow_factory,
            retry_handler=mock_retry_handler,
            notification_service=mock_notification_service,
        )

        await use_case.process_shipped(order_shipped_event_dto)

        mock_uow.order_repo.get_by_id.assert_not_called()

    async def test_process_shipped_wrong_status(
        self,
        order_shipped_event_dto,
        mock_uow_factory,
        mock_retry_handler,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = Order(
            id=order_shipped_event_dto.order_id,
            user_id="user-123",
            item_id=order_shipped_event_dto.item_id,
            quantity=order_shipped_event_dto.quantity,
            status=OrderStatus.NEW,
            payment_id=uuid4(),
            created_at=now,
            updated_at=now,
            idempotency_key=None,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = order

        use_case = ProcessShippingEventUseCase(
            uow_factory=mock_uow_factory,
            retry_handler=mock_retry_handler,
            notification_service=mock_notification_service,
        )

        await use_case.process_shipped(order_shipped_event_dto)

        assert order.status == OrderStatus.NEW
        mock_uow.order_repo.update.assert_not_called()
        mock_notification_service.send_notification.assert_not_called()

    async def test_process_cancelled_success(
        self,
        order_cancelled_event_dto,
        mock_uow_factory,
        mock_retry_handler,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = Order(
            id=order_cancelled_event_dto.order_id,
            user_id="user-123",
            item_id=order_cancelled_event_dto.item_id,
            quantity=order_cancelled_event_dto.quantity,
            status=OrderStatus.PAID,
            payment_id=uuid4(),
            created_at=now,
            updated_at=now,
            idempotency_key=None,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = order

        use_case = ProcessShippingEventUseCase(
            uow_factory=mock_uow_factory,
            retry_handler=mock_retry_handler,
            notification_service=mock_notification_service,
        )

        await use_case.process_cancelled(order_cancelled_event_dto)

        assert order.status == OrderStatus.CANCELLED
        mock_uow.order_repo.update.assert_called()
        mock_notification_service.send_notification.assert_called()

    async def test_process_cancelled_already_shipped(
        self,
        order_cancelled_event_dto,
        mock_uow_factory,
        mock_retry_handler,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = Order(
            id=order_cancelled_event_dto.order_id,
            user_id="user-123",
            item_id=order_cancelled_event_dto.item_id,
            quantity=order_cancelled_event_dto.quantity,
            status=OrderStatus.SHIPPED,
            payment_id=uuid4(),
            created_at=now,
            updated_at=now,
            idempotency_key=None,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = order

        use_case = ProcessShippingEventUseCase(
            uow_factory=mock_uow_factory,
            retry_handler=mock_retry_handler,
            notification_service=mock_notification_service,
        )

        await use_case.process_cancelled(order_cancelled_event_dto)

        assert order.status == OrderStatus.SHIPPED
        mock_uow.order_repo.update.assert_not_called()
        mock_notification_service.send_notification.assert_not_called()

    async def test_process_cancelled_retry_on_error(
        self,
        order_cancelled_event_dto,
        mock_uow_factory,
        mock_retry_handler,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order = Order(
            id=order_cancelled_event_dto.order_id,
            user_id="user-123",
            item_id=order_cancelled_event_dto.item_id,
            quantity=order_cancelled_event_dto.quantity,
            status=OrderStatus.PAID,
            payment_id=uuid4(),
            created_at=now,
            updated_at=now,
            idempotency_key=None,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = order
        mock_uow.commit.side_effect = Exception("Database error")

        use_case = ProcessShippingEventUseCase(
            uow_factory=mock_uow_factory,
            retry_handler=mock_retry_handler,
            notification_service=mock_notification_service,
        )

        await use_case.process_cancelled(order_cancelled_event_dto)

        mock_retry_handler.send_to_retry.assert_called_once()
