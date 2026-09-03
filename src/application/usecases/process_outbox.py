import logging

from src.application.ports import UnitOfWork
from src.infrastructure.messaging.kafka_producer import KafkaProducer
from src.settings import settings

logger = logging.getLogger(__name__)


class ProcessOutboxUseCase:
    """
    Use case for processing pending outbox events.
    Runs periodically to retry failed events.
    """

    def __init__(
        self,
        uow_factory: UnitOfWork,
        kafka_producer: KafkaProducer,
        topic: str | None = None,
    ):
        self.uow_factory = uow_factory
        self.kafka_producer = kafka_producer
        self._config = settings.KAFKA
        self._topic = topic or self._config.ORDER_EVENTS_TOPIC

    async def execute(self, limit: int = 100) -> int:
        """Process pending outbox events."""
        logger.info(f"Processing outbox events (limit={limit})")

        async with self.uow_factory() as uow:
            events = await uow.outbox_repo.get_pending(limit)

        if not events:
            logger.debug("No pending outbox events")
            return 0

        logger.info(f"Found {len(events)} pending outbox events")

        sent_ids = []
        failed_ids = []

        async with self.kafka_producer as producer:
            for event in events:
                try:
                    # Publish event to Kafka
                    await producer.send(
                        topic=self._topic,
                        value={
                            "event_type": event.event_type,
                            "payload": event.payload,
                            "idempotency_key": event.idempotency_key,
                        },
                        key=str(event.id),
                    )
                    sent_ids.append(event.id)
                    logger.debug(f"Event {event.id} sent to Kafka")

                except Exception as e:
                    logger.error(f"Failed to send event {event.id}: {e}")
                    failed_ids.append(event.id)

            # Marking event in outbox
            async with self.uow_factory() as uow:
                for event_id in sent_ids:
                    await uow.outbox_repo.mark_sent(event_id)

                for event_id in failed_ids:
                    await uow.outbox_repo.mark_failed(event_id)

                await uow.commit()
                logger.info(f"Committed: {len(sent_ids)} sent, {len(failed_ids)} failed")

            logger.info(f"Processed {len(sent_ids) + len(failed_ids)} outbox events")
            return len(sent_ids)
