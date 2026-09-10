from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.application.usecases.save_inbox_event import SaveInboxEventUseCase
from src.domain.models import EventType, InboxRecord

pytestmark = pytest.mark.asyncio


@pytest.fixture
def use_case(mock_uow_factory):
    return SaveInboxEventUseCase(uow_factory=mock_uow_factory)


def make_shipped_event(
    order_id: str | None = None,
    shipment_id: str | None = None,
) -> dict:
    """Build a payload matching the order.shipped event schema."""
    return {
        "event_type": EventType.ORDER_SHIPPED.value,
        "order_id": order_id or str(uuid4()),
        "item_id": str(uuid4()),
        "quantity": 1,
        "shipment_id": shipment_id or str(uuid4()),
    }


def make_cancelled_event(
    order_id: str | None = None,
) -> dict:
    """Build a payload matching the order.cancelled event schema."""
    return {
        "event_type": EventType.ORDER_CANCELLED.value,
        "order_id": order_id or str(uuid4()),
        "item_id": str(uuid4()),
        "quantity": 1,
        "reason": "Insufficient stock",
    }


class TestSaveInboxEventExecute:
    """Tests for SaveInboxEventUseCase.execute."""

    async def test_returns_false_when_event_type_missing(self, use_case, mock_uow):
        result = await use_case.execute({})

        assert result is False
        mock_uow.inbox_repo.save.assert_not_awaited()
        mock_uow.commit.assert_not_awaited()

    async def test_returns_false_when_event_type_unknown(self, use_case, mock_uow):
        result = await use_case.execute({"event_type": "unknown.event"})

        assert result is False
        mock_uow.inbox_repo.save.assert_not_awaited()
        mock_uow.commit.assert_not_awaited()

    async def test_saves_order_shipped_event(self, use_case, mock_uow):
        event = make_shipped_event()
        mock_uow.inbox_repo.save.return_value = Mock(spec=InboxRecord)

        result = await use_case.execute(event)

        assert result is True
        mock_uow.inbox_repo.save.assert_awaited_once()
        mock_uow.commit.assert_awaited_once()

        saved_record: InboxRecord = mock_uow.inbox_repo.save.await_args.args[0]
        assert saved_record.event_type == EventType.ORDER_SHIPPED
        assert saved_record.payload == event
        assert saved_record.event_id == f"{EventType.ORDER_SHIPPED.value}_{event['shipment_id']}"

    async def test_saves_order_cancelled_event(self, use_case, mock_uow):
        event = make_cancelled_event()
        mock_uow.inbox_repo.save.return_value = Mock(spec=InboxRecord)

        result = await use_case.execute(event)

        assert result is True
        mock_uow.inbox_repo.save.assert_awaited_once()
        mock_uow.commit.assert_awaited_once()

        saved_record: InboxRecord = mock_uow.inbox_repo.save.await_args.args[0]
        assert saved_record.event_type == EventType.ORDER_CANCELLED
        assert saved_record.payload == event
        assert saved_record.event_id == f"{EventType.ORDER_CANCELLED.value}_{event['order_id']}"

    async def test_returns_false_on_duplicate_event(self, use_case, mock_uow):
        event = make_shipped_event()
        mock_uow.inbox_repo.save.return_value = None

        result = await use_case.execute(event)

        assert result is False
        mock_uow.inbox_repo.save.assert_awaited_once()
        mock_uow.commit.assert_awaited_once()

    async def test_uses_shipment_id_for_shipped_event_id(self, use_case, mock_uow):
        shipment_id = str(uuid4())
        event = make_shipped_event(shipment_id=shipment_id)
        mock_uow.inbox_repo.save.return_value = Mock(spec=InboxRecord)

        await use_case.execute(event)

        saved_record: InboxRecord = mock_uow.inbox_repo.save.await_args.args[0]
        assert saved_record.event_id == f"{EventType.ORDER_SHIPPED.value}_{shipment_id}"

    async def test_uses_order_id_for_cancelled_event_id(self, use_case, mock_uow):
        order_id = str(uuid4())
        event = make_cancelled_event(order_id=order_id)
        mock_uow.inbox_repo.save.return_value = Mock(spec=InboxRecord)

        await use_case.execute(event)

        saved_record: InboxRecord = mock_uow.inbox_repo.save.await_args.args[0]
        assert saved_record.event_id == f"{EventType.ORDER_CANCELLED.value}_{order_id}"

    async def test_commits_even_when_save_returns_none(self, use_case, mock_uow):
        event = make_cancelled_event()
        mock_uow.inbox_repo.save.return_value = None

        await use_case.execute(event)

        mock_uow.commit.assert_awaited_once()
