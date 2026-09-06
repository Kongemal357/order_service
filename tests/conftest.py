from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def mock_notification_service():
    service = Mock()
    service.send_notification = AsyncMock()
    return service


@pytest.fixture
def mock_uow():
    """Mock Unit of Work."""
    uow = Mock()

    # Order repository
    uow.order_repo = Mock()
    uow.order_repo.get_by_idempotency_key = AsyncMock(return_value=None)
    uow.order_repo.get_by_id = AsyncMock()
    uow.order_repo.save = AsyncMock()
    uow.order_repo.update = AsyncMock()

    # Outbox repository
    uow.outbox_repo = Mock()
    uow.outbox_repo.save = AsyncMock()
    uow.outbox_repo.get_pending = AsyncMock(return_value=[])
    uow.outbox_repo.mark_sent = AsyncMock()
    uow.outbox_repo.mark_failed = AsyncMock()

    # Inbox repository
    uow.inbox_repo = Mock()
    uow.inbox_repo.save = AsyncMock()
    uow.inbox_repo.get_by_idempotency_key = AsyncMock(return_value=None)

    # Commit
    uow.commit = AsyncMock()

    # Context manager support
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    return uow


@pytest.fixture
def mock_uow_factory(mock_uow):
    """Mock UoW Factory."""
    factory = Mock()
    factory.return_value = mock_uow
    factory.__call__ = AsyncMock(return_value=mock_uow)
    return factory
