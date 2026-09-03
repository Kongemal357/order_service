import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer

from src.settings import settings

logger = logging.getLogger(__name__)


class KafkaProducer:
    """Kafka producer wrapper with retry logic."""

    def __init__(self):
        self._started = False
        self.producer: AIOKafkaProducer | None = None
        self._config = settings.KAFKA  # 👈 Берем настройки

    async def start(self):
        if self._started:
            return

        self.producer = AIOKafkaProducer(
            bootstrap_servers=self._config.BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks=self._config.ACKS,
            enable_idempotence=self._config.ENABLE_IDEMPOTENCE,
            retry_backoff_ms=self._config.RETRY_BACKOFF_MS,
            max_batch_size=self._config.BATCH_SIZE,
            linger_ms=self._config.LINGER_MS,
            compression_type=self._config.COMPRESSION_TYPE,
            request_timeout_ms=self._config.REQUEST_TIMEOUT_MS,
        )
        await self.producer.start()
        self._started = True

    async def stop(self):
        """Stop the producer."""
        if self.producer:
            await self.producer.stop()
            self._started = False
            logger.info("Kafka producer stopped")

    async def __aenter__(self):
        """Enter context manager."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        await self.stop()

    async def send(self, topic: str, value: dict[str, Any], key: str | None = None):
        """Send message to Kafka."""
        if not self._started:
            await self.start()

        try:
            await self.producer.send(topic, value=value, key=key)
            logger.debug(f"Message sent to {topic}: {value}")
        except Exception as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            raise
