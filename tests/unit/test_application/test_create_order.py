from uuid import uuid4

import pytest

from src.application.dto import CatalogItemDTO
from src.application.usecases.create_order import CreateOrderUseCase
from src.domain.exceptions import CatalogServiceError, InsufficientStockError
from src.domain.models import OrderStatus

pytestmark = pytest.mark.asyncio


class TestCreateOrderUseCase:
    """Tests for CreateOrderUseCase."""

    async def test_create_order_success(
        self,
        create_order_dto,
        catalog_item_dto,
        mock_unit_of_work,
        mock_catalog_client,
    ):
        """Test successful order creation."""
        # Setup mocks
        mock_catalog_client.get_item.return_value = catalog_item_dto
        mock_unit_of_work.order_repo.get_by_idempotency_key.return_value = None

        def save_order_side_effect(order):
            # Simulate saving
            return order

        mock_unit_of_work.order_repo.save.side_effect = save_order_side_effect

        # Execute use case
        use_case = CreateOrderUseCase(mock_unit_of_work, mock_catalog_client)
        result = await use_case.execute(create_order_dto)

        # Assert
        assert result.user_id == create_order_dto.user_id
        assert result.item_id == create_order_dto.item_id
        assert result.quantity == create_order_dto.quantity
        assert result.status == OrderStatus.NEW
        assert result.idempotency_key == create_order_dto.idempotency_key

        mock_catalog_client.get_item.assert_called_once_with(create_order_dto.item_id)
        mock_unit_of_work.order_repo.save.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()

    async def test_create_order_idempotent(
        self,
        create_order_dto,
        sample_order,
        mock_unit_of_work,
        mock_catalog_client,
    ):
        """Test idempotent request returns existing order."""
        # Setup mocks
        mock_unit_of_work.order_repo.get_by_idempotency_key.return_value = sample_order

        # Execute use case
        use_case = CreateOrderUseCase(mock_unit_of_work, mock_catalog_client)
        result = await use_case.execute(create_order_dto)

        # Assert
        assert result.id == sample_order.id
        assert result.status == sample_order.status

        # Save should NOT be called
        mock_unit_of_work.order_repo.save.assert_not_called()
        mock_catalog_client.get_item.assert_not_called()

    async def test_create_order_insufficient_stock(
        self,
        create_order_dto,
        mock_unit_of_work,
        mock_catalog_client,
    ):
        """Test order creation with insufficient stock."""
        # Setup mock - only 1 item available, but we need 3
        catalog_item = CatalogItemDTO(
            id=uuid4(),
            name="Test Product",
            price="100.00",
            available_qty=1,
            created_at=None,
        )
        mock_catalog_client.get_item.return_value = catalog_item
        mock_unit_of_work.order_repo.get_by_idempotency_key.return_value = None

        # Execute use case
        use_case = CreateOrderUseCase(mock_unit_of_work, mock_catalog_client)

        with pytest.raises(InsufficientStockError) as exc_info:
            await use_case.execute(create_order_dto)

        assert "Not enough stock" in str(exc_info.value)
        mock_unit_of_work.order_repo.save.assert_not_called()
        mock_unit_of_work.commit.assert_not_called()

    async def test_create_order_catalog_error(
        self,
        create_order_dto,
        mock_unit_of_work,
        mock_catalog_client,
    ):
        """Test order creation when Catalog Service fails."""
        # Setup mock
        mock_catalog_client.get_item.side_effect = CatalogServiceError("Service unavailable")
        mock_unit_of_work.order_repo.get_by_idempotency_key.return_value = None

        # Execute use case
        use_case = CreateOrderUseCase(mock_unit_of_work, mock_catalog_client)

        with pytest.raises(CatalogServiceError):
            await use_case.execute(create_order_dto)

        mock_unit_of_work.order_repo.save.assert_not_called()
        mock_unit_of_work.commit.assert_not_called()
