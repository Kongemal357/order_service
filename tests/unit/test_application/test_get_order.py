from uuid import uuid4

import pytest

from src.application.usecases.get_order import GetOrderUseCase
from src.domain.exceptions import OrderNotFoundError

pytestmark = pytest.mark.asyncio


class TestGetOrderUseCase:
    """Tests for GetOrderUseCase."""

    async def test_get_order_success(self, sample_order, mock_unit_of_work):
        """Test successful order retrieval."""
        # Setup mock
        mock_unit_of_work.order_repo.get_by_id.return_value = sample_order

        # Execute use case
        use_case = GetOrderUseCase(mock_unit_of_work)
        result = await use_case.execute(sample_order.id)

        # Assert
        assert result.id == sample_order.id
        assert result.user_id == sample_order.user_id
        assert result.status == sample_order.status

        mock_unit_of_work.order_repo.get_by_id.assert_called_once_with(sample_order.id)

    async def test_get_order_not_found(self, mock_unit_of_work):
        """Test order retrieval when not found."""
        # Setup mock
        order_id = uuid4()
        mock_unit_of_work.order_repo.get_by_id.return_value = None

        # Execute use case
        use_case = GetOrderUseCase(mock_unit_of_work)

        with pytest.raises(OrderNotFoundError) as exc_info:
            await use_case.execute(order_id)

        assert str(order_id) in str(exc_info.value)
        mock_unit_of_work.order_repo.get_by_id.assert_called_once_with(order_id)
