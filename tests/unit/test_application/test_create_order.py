from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.application.dto import CreateOrderDTO
from src.application.usecases.create_order import CreateOrderUseCase
from src.domain.exceptions import InsufficientStockError, PaymentError
from src.domain.models import Order, OrderStatus

pytestmark = pytest.mark.asyncio


@pytest.fixture
def create_order_dto():
    return CreateOrderDTO(
        user_id="user-123",
        item_id=uuid4(),
        quantity=1,
        idempotency_key="test-idempotency-key",
    )


@pytest.fixture
def mock_catalog_client():
    client = Mock()
    client.get_item = AsyncMock(
        return_value=Mock(
            price="100.00",
            available_qty=10,
        )
    )
    return client


@pytest.fixture
def mock_payment_client():
    client = Mock()
    client.create_payment = AsyncMock(
        return_value=Mock(
            id=uuid4(),
            status="pending",
        )
    )
    return client


class TestCreateOrderUseCase:
    async def test_create_order_success(
        self,
        create_order_dto,
        mock_uow_factory,
        mock_catalog_client,
        mock_payment_client,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        saved_order = Order(
            id=uuid4(),
            user_id=create_order_dto.user_id,
            item_id=create_order_dto.item_id,
            quantity=create_order_dto.quantity,
            status=OrderStatus.NEW,
            payment_id=None,
            created_at=now,
            updated_at=now,
            idempotency_key=create_order_dto.idempotency_key,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.save.return_value = saved_order
        mock_uow.order_repo.get_by_id.return_value = saved_order

        use_case = CreateOrderUseCase(
            uow_factory=mock_uow_factory,
            catalog_client=mock_catalog_client,
            payment_client=mock_payment_client,
            notification_service=mock_notification_service,
        )

        result = await use_case.execute(create_order_dto)

        assert result.user_id == create_order_dto.user_id
        assert result.status == OrderStatus.NEW.value
        assert result.id == saved_order.id

        mock_catalog_client.get_item.assert_called_once()
        mock_uow.order_repo.save.assert_called_once()
        mock_notification_service.send_notification.assert_called_once()
        mock_payment_client.create_payment.assert_called_once()

    async def test_create_order_idempotent(
        self,
        create_order_dto,
        mock_uow_factory,
        mock_catalog_client,
        mock_payment_client,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        existing_order = Order(
            id=uuid4(),
            user_id=create_order_dto.user_id,
            item_id=create_order_dto.item_id,
            quantity=create_order_dto.quantity,
            status=OrderStatus.NEW,
            payment_id=None,
            created_at=now,
            updated_at=now,
            idempotency_key=create_order_dto.idempotency_key,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_idempotency_key.return_value = existing_order

        use_case = CreateOrderUseCase(
            uow_factory=mock_uow_factory,
            catalog_client=mock_catalog_client,
            payment_client=mock_payment_client,
            notification_service=mock_notification_service,
        )

        result = await use_case.execute(create_order_dto)

        assert result.id == existing_order.id
        mock_catalog_client.get_item.assert_not_called()
        mock_uow.order_repo.save.assert_not_called()
        mock_payment_client.create_payment.assert_not_called()

    async def test_create_order_insufficient_stock(
        self,
        create_order_dto,
        mock_uow_factory,
        mock_catalog_client,
        mock_payment_client,
        mock_notification_service,
    ):
        mock_catalog_client.get_item.return_value = Mock(
            price="100.00",
            available_qty=0,
        )

        use_case = CreateOrderUseCase(
            uow_factory=mock_uow_factory,
            catalog_client=mock_catalog_client,
            payment_client=mock_payment_client,
            notification_service=mock_notification_service,
        )

        with pytest.raises(InsufficientStockError):
            await use_case.execute(create_order_dto)

        mock_uow_factory.return_value.order_repo.save.assert_not_called()

    async def test_create_order_payment_fails(
        self,
        create_order_dto,
        mock_uow_factory,
        mock_catalog_client,
        mock_payment_client,
        mock_notification_service,
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        saved_order = Order(
            id=uuid4(),
            user_id=create_order_dto.user_id,
            item_id=create_order_dto.item_id,
            quantity=create_order_dto.quantity,
            status=OrderStatus.NEW,
            payment_id=None,
            created_at=now,
            updated_at=now,
            idempotency_key=create_order_dto.idempotency_key,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.save.return_value = saved_order
        mock_uow.order_repo.get_by_id.return_value = saved_order
        mock_payment_client.create_payment.side_effect = PaymentError("Payment failed")

        use_case = CreateOrderUseCase(
            uow_factory=mock_uow_factory,
            catalog_client=mock_catalog_client,
            payment_client=mock_payment_client,
            notification_service=mock_notification_service,
        )

        with pytest.raises(PaymentError):
            await use_case.execute(create_order_dto)

        mock_uow.order_repo.update.assert_called()
        mock_notification_service.send_notification.assert_called()
