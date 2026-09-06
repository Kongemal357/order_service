from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.application.usecases.get_order import GetOrderUseCase
from src.domain.exceptions import OrderNotFoundError
from src.domain.models import Order, OrderStatus

pytestmark = pytest.mark.asyncio


class TestGetOrderUseCase:
    """Tests for GetOrderUseCase."""

    async def test_get_order_success(self, mock_uow_factory):
        # Given
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order_id = uuid4()
        expected_order = Order(
            id=order_id,
            user_id="user-123",
            item_id=uuid4(),
            quantity=1,
            status=OrderStatus.NEW,
            payment_id=None,
            created_at=now,
            updated_at=now,
            idempotency_key=None,
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = expected_order

        use_case = GetOrderUseCase(uow_factory=mock_uow_factory)

        result = await use_case.execute(order_id)

        assert result.id == expected_order.id
        assert result.user_id == expected_order.user_id
        assert result.status == OrderStatus.NEW.value
        mock_uow.order_repo.get_by_id.assert_called_once_with(order_id)

    async def test_get_order_not_found(self, mock_uow_factory):
        order_id = uuid4()

        mock_uow = mock_uow_factory.return_value
        mock_uow.order_repo.get_by_id.return_value = None

        use_case = GetOrderUseCase(uow_factory=mock_uow_factory)

        with pytest.raises(OrderNotFoundError) as exc_info:
            await use_case.execute(order_id)

        assert str(order_id) in str(exc_info.value)
        mock_uow.order_repo.get_by_id.assert_called_once_with(order_id)
