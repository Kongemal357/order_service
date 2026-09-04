import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from aiokafka import AIOKafkaConsumer

from src.infrastructure.messaging.retry_handler import RetryHandler
from src.settings import kafka_settings

logger = logging.getLogger(__name__)


class KafkaConsumer:
    """
    Kafka consumer with adaptive batching.

    Accumulates messages until:
    1. Batch size reaches min_batch_size
    2. Max wait time is exceeded (since first message)
    3. Batch size reaches max_batch_size (hard limit)
    """

    def __init__(
        self,
        handler: Callable[[list[dict]], Awaitable[None]],
        topics: list[str] | None = None,
        group_id: str | None = None,
        min_batch_size: int | None = None,
        max_batch_size: int | None = None,
        max_wait_time: float | None = None,
        poll_timeout_ms: int | None = None,
        retry_handler: Optional[RetryHandler] = None,
    ):
        self._config = kafka_settings

        self._topics = topics or [self._config.SHIPMENT_EVENTS_TOPIC]
        self._group_id = group_id or self._config.CONSUMER_GROUP_ID
        self._handler = handler
        self._min_batch_size = min_batch_size or self._config.MIN_BATCH_SIZE
        self._max_batch_size = max_batch_size or self._config.MAX_BATCH_SIZE
        self._max_wait_time = max_wait_time or self._config.MAX_WAIT_TIME
        self._poll_timeout_ms = poll_timeout_ms or self._config.POLL_TIMEOUT_MS
        self._retry_handler = retry_handler

        self._consumer: Optional[AIOKafkaConsumer] = None
        self._message_buffer: deque = deque()
        self._first_message_time: Optional[datetime] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the consumer."""
        if self._running:
            return

        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._config.BOOTSTRAP_SERVERS,
            group_id=self._group_id,
            enable_auto_commit=False,
            max_poll_records=self._max_batch_size,
            auto_offset_reset="earliest",
        )
        await self._consumer.start()

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(
            f"Adaptive batch processor started for topics: {self._topics} "
            f"(min_batch={self._min_batch_size}, max_batch={self._max_batch_size}, "
            f"max_wait={self._max_wait_time}s)"
        )

    async def stop(self):
        """Stop the consumer."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._consumer:
            await self._consumer.stop()
            self._consumer = None

        logger.info("Adaptive batch processor stopped")

    async def _run(self):
        """Main consumer loop."""
        while self._running:
            try:
                # Poll for messages
                batch = await self._consumer.getmany(
                    timeout_ms=self._poll_timeout_ms,
                    max_records=self._max_batch_size,
                )

                # Add messages to buffer
                for topic_partition, messages in batch.items():
                    if messages:
                        self._message_buffer.extend(messages)
                        if not self._first_message_time:
                            self._first_message_time = datetime.now(timezone.utc).replace(
                                tzinfo=None
                            )
                        logger.debug(
                            f"Added {len(messages)} messages to buffer "
                            f"(total: {len(self._message_buffer)})"
                        )

                # Check if we should process the batch
                if self._should_process_batch():
                    await self._process_batch()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(1)

        # Process remaining messages on shutdown
        if self._message_buffer:
            logger.info(f"Processing {len(self._message_buffer)} remaining messages on shutdown")
            await self._process_batch()

    def _should_process_batch(self) -> bool:
        """Check if batch should be processed."""
        if not self._message_buffer:
            return False

        # Process an incomplete batch when the maximum waiting time has expired.
        if self._first_message_time:
            current_time = datetime.now(timezone.utc).replace(tzinfo=None)
            elapsed = (current_time - self._first_message_time).total_seconds()
            if elapsed >= self._max_wait_time:
                logger.debug(
                    f"Wait time exceeded ({elapsed:.2f}s), "
                    f"processing {len(self._message_buffer)} messages"
                )
                return True

        # Hard limit: max batch size reached
        if len(self._message_buffer) >= self._max_batch_size:
            logger.debug(f"Max batch size reached: {len(self._message_buffer)}")
            return True

        # Min batch size reached AND enough time has passed
        if len(self._message_buffer) >= self._min_batch_size:
            if self._first_message_time:
                current_time = datetime.now(timezone.utc).replace(tzinfo=None)
                elapsed = (current_time - self._first_message_time).total_seconds()
                if elapsed >= self._max_wait_time:
                    logger.debug(
                        f"Min batch size reached ({len(self._message_buffer)}) "
                        f"and wait time exceeded ({elapsed:.2f}s)"
                    )
                    return True

        return False

    async def _process_batch(self):
        """Process accumulated batch."""
        if not self._message_buffer:
            return

        # Calculate batch size (respect max limit)
        batch_size = min(len(self._message_buffer), self._max_batch_size)
        batch = []

        for _ in range(batch_size):
            if self._message_buffer:
                batch.append(self._message_buffer.popleft())

        # Reset timer
        self._first_message_time = None

        # Extract data from messages
        try:
            data_list = []
            for msg in batch:
                try:
                    data = json.loads(msg.value.decode())
                    data_list.append(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                    # Still commit to avoid reprocessing
                    continue

            if not data_list:
                await self._consumer.commit()
                return

            logger.info(f"Processing batch of {len(data_list)} messages")

            # Call handler
            await self._handler(data_list)

            # Commit offset for all messages in batch
            await self._consumer.commit()
            logger.debug(f"Batch of {len(data_list)} messages committed")

        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            await self._handle_batch_error(batch, e)

    async def consume(self):
        """
        Public method to start consuming messages.
        Wraps the internal _run() method.
        """
        await self._run()

    async def _handle_batch_error(self, batch: list, error: Exception):
        """
        Handle batch processing error.
        Sends failed messages to retry topic (or DLQ after max retries).
        """
        logger.error(f"Batch error: {error}")

        if not self._retry_handler:
            logger.warning("No retry handler configured, messages will be reprocessed")
            return

        for msg in batch:
            try:
                data = json.loads(msg.value.decode())
                await self._retry_handler.send_to_retry(
                    event_data=data,
                    retry_count=1,
                    error=str(error),
                )
                logger.debug(f"Message sent to retry topic: {data.get('event_type')}")
            except Exception as e:
                logger.error(f"Failed to send message to retry: {e}")

        await self._consumer.commit()
