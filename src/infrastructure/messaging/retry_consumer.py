import asyncio
import json
import logging
import time
from typing import Optional

from aiokafka import AIOKafkaConsumer

from src.infrastructure.messaging.kafka_producer import KafkaProducer
from src.settings import settings

logger = logging.getLogger(__name__)


class RetryConsumer:
    """
    Consumer for retry topic.

    Reads events from retry topic and sends them back to main topic
    after the configured delay.
    """

    def __init__(
        self,
        producer: KafkaProducer,
        main_topic: Optional[str] = None,
        retry_topic: Optional[str] = None,
        group_id: Optional[str] = None,
    ):
        self._config = settings.KAFKA
        self._producer = producer
        self._main_topic = main_topic or self._config.SHIPMENT_EVENTS_TOPIC
        self._retry_topic = retry_topic or self._config.SHIPMENT_EVENTS_RETRY_TOPIC
        self._group_id = group_id or "retry-processors"

        self._consumer: AIOKafkaConsumer | None = None
        self._running = False
        self._max_retries = self._config.MAX_RETRIES

    async def start(self):
        """Start retry consumer."""
        self._consumer = AIOKafkaConsumer(
            self._retry_topic,
            bootstrap_servers=self._config.BOOTSTRAP_SERVERS,
            group_id=self._group_id,
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode()),
        )
        await self._consumer.start()
        self._running = True
        logger.info(f"Retry consumer started for topic: {self._retry_topic}")

    async def stop(self):
        """Stop retry consumer."""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            self._consumer = None
            logger.info("Retry consumer stopped")

    async def consume(self):
        """Consume messages from retry topic with proper shutdown."""
        if not self._consumer:
            await self.start()

        try:
            while self._running:
                messages = await self._consumer.getmany(
                    timeout_ms=1000,
                    max_records=100,
                )

                if not messages:
                    continue

                for topic_partition, msgs in messages.items():
                    for message in msgs:
                        if not self._running:
                            break
                        await self._process_message(message)

                    await self._consumer.commit()

        except asyncio.CancelledError:
            logger.info("Retry consumer cancelled")
            raise
        except Exception as e:
            logger.error(f"Retry consumer error: {e}")
            raise
        finally:
            await self.stop()

    async def _process_message(self, message):
        """Process single retry message."""
        try:
            retry_data = message.value
            retry_count = retry_data.get("retry_count", 1)
            retry_at = retry_data.get("retry_at", 0)
            event_data = retry_data.get("event_data", {})

            # Check if delay has passed
            current_time = int(time.time())
            if current_time < retry_at:
                # In production, you'd use a delayed queue or scheduler
                logger.debug(f"Retry not yet due ({retry_at - current_time}s remaining)")
                return

            # Send back to main topic
            await self._producer.send(
                topic=self._main_topic,
                value=event_data,
                key=message.key,
            )

            logger.info(f"Event sent back to main topic (retry {retry_count})")

        except Exception as e:
            logger.error(f"Error processing retry message: {e}")
            raise
