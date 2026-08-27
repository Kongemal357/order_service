from datetime import timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.application.dto import CatalogItemDTO, CreateOrderDTO
from src.application.ports import CatalogClient, UnitOfWork
from src.domain.models import Order, OrderStatus

# ============ Domain Fixtures ============


@pytest.fixture
def sample_order_data():
    """Sample order data for tests."""
    return {
        "id": uuid4(),
        "user_id": "user-123",
        "item_id": uuid4(),
        "quantity": 3,
        "status": OrderStatus.NEW,
        "created_at": None,  # Will be set in test
        "updated_at": None,
        "idempotency_key": "test-key-123",
    }


@pytest.fixture
def sample_order(sample_order_data) -> Order:
    """Create a sample order."""
    from datetime import datetime

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return Order(
        id=sample_order_data["id"],
        user_id=sample_order_data["user_id"],
        item_id=sample_order_data["item_id"],
        quantity=sample_order_data["quantity"],
        status=sample_order_data["status"],
        created_at=now,
        updated_at=now,
        idempotency_key=sample_order_data["idempotency_key"],
    )


# ============ Application DTO Fixtures ============


@pytest.fixture
def create_order_dto() -> CreateOrderDTO:
    """Create Order DTO fixture."""
    return CreateOrderDTO(
        user_id="user-123",
        item_id=uuid4(),
        quantity=3,
        idempotency_key="test-key-123",
    )


@pytest.fixture
def catalog_item_dto() -> CatalogItemDTO:
    """Catalog Item DTO fixture."""
    return CatalogItemDTO(
        id=uuid4(),
        name="Test Product",
        price="100.00",
        available_qty=10,
        created_at=None,
    )


# ============ Mock Fixtures ============


@pytest.fixture
def mock_catalog_client() -> Mock:
    """Mock Catalog Client."""
    client = Mock(spec=CatalogClient)
    client.get_item = AsyncMock()
    return client


@pytest.fixture
def mock_unit_of_work() -> Mock:
    """Mock Unit of Work."""
    uow = Mock(spec=UnitOfWork)
    uow.order_repo = Mock()
    uow.order_repo.save = AsyncMock()
    uow.order_repo.get_by_id = AsyncMock()
    uow.order_repo.get_by_idempotency_key = AsyncMock()
    uow.order_repo.update = AsyncMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()

    # Context manager support
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    return uow
