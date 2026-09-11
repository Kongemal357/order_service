import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.application.usecases.process_inbox import ProcessInboxUseCase
from src.application.usecases.process_shipping_event import ProcessShippingEventUseCase
from src.domain.models import EventType, InboxRecord

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_shipping_use_case():
    use_case = Mock(spec=ProcessShippingEventUseCase)
    use_case.process_shipped = AsyncMock(return_value=True)
    use_case.process_cancelled = AsyncMock(return_value=True)
    use_case.send_notifications = AsyncMock()
    return use_case


@pytest.fixture
def use_case(mock_uow_factory, mock_shipping_use_case):
    return ProcessInboxUseCase(
        uow_factory=mock_uow_factory,
        shipping_use_case=mock_shipping_use_case,
    )


def make_inbox_record(
    event_type: EventType,
    payload: dict | None = None,
) -> InboxRecord:
    """Create an InboxRecord with the given event type and payload."""
    return InboxRecord.create(
        event_id=f"event-{uuid4()}",
        event_type=event_type,
        payload=payload or {"order_id": str(uuid4())},
    )


def make_shipped_payload(order_id: str | None = None) -> dict:
    """Full payload matching the order.shipped event schema."""
    return {
        "order_id": order_id or str(uuid4()),
        "item_id": str(uuid4()),
        "quantity": 1,
        "shipment_id": str(uuid4()),
    }


def make_cancelled_payload(order_id: str | None = None) -> dict:
    """Full payload matching the order.cancelled event schema."""
    return {
        "order_id": order_id or str(uuid4()),
        "item_id": str(uuid4()),
        "quantity": 1,
        "reason": "Insufficient stock",
    }


class TestProcessInboxExecute:
    """Tests for ProcessInboxUseCase.execute."""

    async def test_returns_zero_when_no_pending_events(self, use_case, mock_uow):
        mock_uow.inbox_repo.get_pending.return_value = []

        result = await use_case.execute(limit=100)

        assert result == 0
        mock_uow.inbox_repo.get_pending.assert_awaited_once_with(100)

    async def test_processes_order_shipped_event(self, use_case, mock_uow, mock_shipping_use_case):
        order_id = uuid4()
        event = make_inbox_record(
            EventType.ORDER_SHIPPED,
            make_shipped_payload(str(order_id)),
        )
        mock_uow.inbox_repo.get_pending.return_value = [event]

        result = await use_case.execute(limit=100)

        assert result == 1
        mock_shipping_use_case.process_shipped.assert_awaited_once()
        mock_uow.inbox_repo.mark_processed.assert_awaited_once_with(event.id)
        mock_uow.commit.assert_awaited()

    async def test_processes_order_cancelled_event(
        self, use_case, mock_uow, mock_shipping_use_case
    ):
        order_id = uuid4()
        event = make_inbox_record(
            EventType.ORDER_CANCELLED,  # ← было ORDER_SHIPPED
            make_cancelled_payload(str(order_id)),  # ← полный payload
        )
        mock_uow.inbox_repo.get_pending.return_value = [event]

        result = await use_case.execute(limit=100)

        assert result == 1
        mock_shipping_use_case.process_cancelled.assert_awaited_once()
        mock_shipping_use_case.process_shipped.assert_not_awaited()
        mock_uow.inbox_repo.mark_processed.assert_awaited_once_with(event.id)
        mock_uow.commit.assert_awaited()

    async def test_skips_unknown_event_type(self, use_case, mock_uow, mock_shipping_use_case):
        event = make_inbox_record(EventType.ORDER_SHIPPED)
        event.event_type = "unknown.event"
        mock_uow.inbox_repo.get_pending.return_value = [event]

        result = await use_case.execute(limit=100)

        assert result == 0
        mock_shipping_use_case.process_shipped.assert_not_awaited()
        mock_shipping_use_case.process_cancelled.assert_not_awaited()
        mock_uow.inbox_repo.mark_processed.assert_awaited_once_with(event.id)
        mock_uow.commit.assert_awaited()

    async def test_continues_when_one_event_fails(self, use_case, mock_uow, mock_shipping_use_case):
        failed_event = make_inbox_record(
            EventType.ORDER_SHIPPED,
            make_shipped_payload(),  # ← полный payload
        )
        successful_event = make_inbox_record(
            EventType.ORDER_SHIPPED,
            make_shipped_payload(),  # ← полный payload
        )
        mock_uow.inbox_repo.get_pending.return_value = [failed_event, successful_event]
        mock_shipping_use_case.process_shipped.side_effect = [
            Exception("boom"),
            True,
        ]

        result = await use_case.execute(limit=100)

        assert result == 1
        assert mock_shipping_use_case.process_shipped.await_count == 2

    async def test_does_not_send_notification_when_use_case_returns_false(
        self, use_case, mock_uow, mock_shipping_use_case
    ):
        event = make_inbox_record(
            EventType.ORDER_SHIPPED,
            make_shipped_payload(),  # ← полный payload
        )
        mock_uow.inbox_repo.get_pending.return_value = [event]
        mock_shipping_use_case.process_shipped.return_value = False

        result = await use_case.execute(limit=100)

        assert result == 1
        mock_shipping_use_case.send_notifications.assert_not_awaited()

    async def test_sends_notification_on_success(self, use_case, mock_uow, mock_shipping_use_case):
        order_id = str(uuid4())
        event = make_inbox_record(
            EventType.ORDER_SHIPPED,
            make_shipped_payload(order_id),
        )
        mock_uow.inbox_repo.get_pending.return_value = [event]
        mock_shipping_use_case.process_shipped.return_value = True

        await use_case.execute(limit=100)
        await asyncio.sleep(0)

        mock_shipping_use_case.send_notifications.assert_awaited_once_with(
            order_id=order_id,
            event_type=EventType.ORDER_SHIPPED,
        )

    async def test_notification_failure_does_not_break_processing(
        self, use_case, mock_uow, mock_shipping_use_case
    ):
        event = make_inbox_record(
            EventType.ORDER_SHIPPED,
            make_shipped_payload(),  # ← полный payload
        )
        mock_uow.inbox_repo.get_pending.return_value = [event]
        mock_shipping_use_case.process_shipped.return_value = True
        mock_shipping_use_case.send_notifications.side_effect = RuntimeError("nope")

        result = await use_case.execute(limit=100)

        assert result == 1
        mock_uow.inbox_repo.mark_processed.assert_awaited_once_with(event.id)
        mock_uow.commit.assert_awaited()

    async def test_processes_multiple_events(self, use_case, mock_uow, mock_shipping_use_case):
        events = [
            make_inbox_record(EventType.ORDER_SHIPPED, make_shipped_payload()),
            make_inbox_record(EventType.ORDER_CANCELLED, make_cancelled_payload()),
            make_inbox_record(EventType.ORDER_SHIPPED, make_shipped_payload()),
        ]
        mock_uow.inbox_repo.get_pending.return_value = events

        result = await use_case.execute(limit=100)

        assert result == 3
        assert mock_shipping_use_case.process_shipped.await_count == 2
        assert mock_shipping_use_case.process_cancelled.await_count == 1
        mock_uow.inbox_repo.mark_processed.assert_awaited()
        assert mock_uow.inbox_repo.mark_processed.await_count == 3
