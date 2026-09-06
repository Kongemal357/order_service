from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.usecases.process_outbox import ProcessOutboxUseCase
from src.domain.models import OutboxEvent
from src.infrastructure.messaging.kafka_producer import KafkaProducer

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer with spec."""
    producer = AsyncMock(spec=KafkaProducer)
    producer.send = AsyncMock()
    producer.start = AsyncMock()
    producer.stop = AsyncMock()

    # Context manager support
    producer.__aenter__ = AsyncMock(return_value=producer)
    producer.__aexit__ = AsyncMock(return_value=None)

    return producer


class TestProcessOutboxUseCase:
    async def test_process_outbox_success(
        self,
        mock_uow_factory,
        mock_kafka_producer,
    ):
        # Given
        outbox_event = OutboxEvent.create(
            event_type="order.paid",
            payload={"order_id": str(uuid4())},
            idempotency_key="test-key",
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.outbox_repo.get_pending.return_value = [outbox_event]
        mock_uow.outbox_repo.mark_sent = AsyncMock()
        mock_uow.outbox_repo.mark_failed = AsyncMock()
        mock_uow.commit = AsyncMock()

        use_case = ProcessOutboxUseCase(
            uow_factory=mock_uow_factory,
            kafka_producer=mock_kafka_producer,
        )

        # When
        result = await use_case.execute(limit=10)

        # Then
        assert result == 1
        mock_uow.outbox_repo.get_pending.assert_called_once_with(10)
        mock_uow.outbox_repo.mark_sent.assert_called_once_with(outbox_event.id)
        mock_uow.outbox_repo.mark_failed.assert_not_called()
        mock_uow.commit.assert_called_once()
        mock_kafka_producer.send.assert_called_once()

    async def test_process_outbox_no_events(
        self,
        mock_uow_factory,
        mock_kafka_producer,
    ):
        # Given
        mock_uow = mock_uow_factory.return_value
        mock_uow.outbox_repo.get_pending.return_value = []
        mock_uow.commit = AsyncMock()

        use_case = ProcessOutboxUseCase(
            uow_factory=mock_uow_factory,
            kafka_producer=mock_kafka_producer,
        )

        # When
        result = await use_case.execute(limit=10)

        # Then
        assert result == 0
        mock_uow.outbox_repo.get_pending.assert_called_once_with(10)
        mock_uow.outbox_repo.mark_sent.assert_not_called()
        mock_uow.outbox_repo.mark_failed.assert_not_called()
        mock_uow.commit.assert_not_called()
        mock_kafka_producer.send.assert_not_called()

    async def test_process_outbox_failure(
        self,
        mock_uow_factory,
        mock_kafka_producer,
    ):
        # Given
        outbox_event = OutboxEvent.create(
            event_type="order.paid",
            payload={"order_id": str(uuid4())},
            idempotency_key="test-key",
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.outbox_repo.get_pending.return_value = [outbox_event]
        mock_uow.outbox_repo.mark_sent = AsyncMock()
        mock_uow.outbox_repo.mark_failed = AsyncMock()
        mock_uow.commit = AsyncMock()
        mock_kafka_producer.send.side_effect = Exception("Kafka error")

        use_case = ProcessOutboxUseCase(
            uow_factory=mock_uow_factory,
            kafka_producer=mock_kafka_producer,
        )

        # When
        result = await use_case.execute(limit=10)

        # Then
        assert result == 0
        mock_uow.outbox_repo.get_pending.assert_called_once_with(10)
        mock_uow.outbox_repo.mark_sent.assert_not_called()
        mock_uow.outbox_repo.mark_failed.assert_called_once_with(outbox_event.id)
        mock_uow.commit.assert_called_once()
        mock_kafka_producer.send.assert_called_once()

    async def test_process_outbox_multiple_events(
        self,
        mock_uow_factory,
        mock_kafka_producer,
    ):
        # Given
        event1 = OutboxEvent.create(
            event_type="order.paid",
            payload={"order_id": str(uuid4())},
            idempotency_key="test-key-1",
        )
        event2 = OutboxEvent.create(
            event_type="order.paid",
            payload={"order_id": str(uuid4())},
            idempotency_key="test-key-2",
        )

        mock_uow = mock_uow_factory.return_value
        mock_uow.outbox_repo.get_pending.return_value = [event1, event2]
        mock_uow.outbox_repo.mark_sent = AsyncMock()
        mock_uow.outbox_repo.mark_failed = AsyncMock()
        mock_uow.commit = AsyncMock()

        use_case = ProcessOutboxUseCase(
            uow_factory=mock_uow_factory,
            kafka_producer=mock_kafka_producer,
        )

        # When
        result = await use_case.execute(limit=10)

        # Then
        assert result == 2
        assert mock_uow.outbox_repo.mark_sent.call_count == 2
        assert mock_kafka_producer.send.call_count == 2
