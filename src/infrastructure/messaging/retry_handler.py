import logging
import time
from typing import Optional

from src.infrastructure.messaging.kafka_producer import KafkaProducer
from src.settings import settings

logger = logging.getLogger(__name__)


class RetryHandler:
    """
    Handler for sending events to retry topic.
    Used when main consumer fails to process an event.
    """

    def __init__(self, producer: KafkaProducer):
        self._producer = producer
        self._config = settings.KAFKA
        self._retry_topic = self._config.SHIPMENT_EVENTS_RETRY_TOPIC
        self._dlq_topic = self._config.SHIPMENT_EVENTS_DLQ_TOPIC
        self._max_retries = self._config.MAX_RETRIES
        self._retry_delays = self._config.RETRY_DELAYS

    async def send_to_retry(
        self,
        event_data: dict,
        retry_count: int = 1,
        error: Optional[str] = None,
    ) -> None:
        """
        Send failed event to retry topic.

        Args:
            event_data: Original event data
            retry_count: Current retry count
            error: Error message
        """
        if retry_count >= self._max_retries:
            # Max retries exceeded → DLQ
            logger.error(f"Event exceeded max retries ({self._max_retries}), sending to DLQ")
            await self._send_to_dlq(event_data, retry_count, error)
            return

        # Calculate delay
        delay = (
            self._retry_delays[retry_count - 1] if retry_count <= len(self._retry_delays) else 60
        )

        retry_data = {
            "event_data": event_data,
            "retry_count": retry_count,
            "retry_at": int(time.time()) + delay,
            "error": error,
            "original_topic": self._config.SHIPMENT_EVENTS_TOPIC,
        }

        await self._producer.send(
            topic=self._retry_topic,
            value=retry_data,
            key=event_data.get("order_id"),
        )

        logger.info(
            f"Event sent to retry topic (retry {retry_count}/{self._max_retries}, delay: {delay}s)"
        )

    async def _send_to_dlq(self, event_data: dict, retry_count: int, error: Optional[str]) -> None:
        """Send event to Dead Letter Queue."""
        dlq_data = {
            "event_data": event_data,
            "retry_count": retry_count,
            "error": error,
            "failed_at": time.time(),
            "original_topic": self._config.SHIPMENT_EVENTS_TOPIC,
        }

        await self._producer.send(
            topic=self._dlq_topic,
            value=dlq_data,
            key=event_data.get("order_id"),
        )
        logger.warning(f"Event sent to DLQ: {event_data.get('order_id')}")
