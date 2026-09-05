import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI
from src.application.dto.event_dto import OrderCancelledEventDTO, OrderShippedEventDTO
from src.application.usecases.process_outbox import ProcessOutboxUseCase
from src.application.usecases.process_shipping_event import ProcessShippingEventUseCase
from src.infrastructure.messaging.kafka_consumer import KafkaConsumer
from src.infrastructure.messaging.kafka_producer import KafkaProducer
from src.infrastructure.messaging.retry_consumer import RetryConsumer
from src.infrastructure.persistence.database import engine
from src.infrastructure.workers.outbox_worker import OutboxWorker
from src.presentation.api.dependencies import (
    get_notification_service,
    get_retry_handler,
    get_uow_factory,
)
from src.presentation.api.routes.orders import router
from src.settings import settings

logger = logging.getLogger(__name__)

# Global components
_kafka_producer: KafkaProducer | None = None
_kafka_consumer: KafkaConsumer | None = None
_retry_consumer: RetryConsumer | None = None
_outbox_worker: OutboxWorker | None = None
_consumer_task: asyncio.Task | None = None
_retry_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for Kafka and Outbox worker."""
    global _kafka_producer, _kafka_consumer, _retry_consumer, _outbox_worker
    global _consumer_task, _retry_task

    logger.info("Starting up...")

    # 1. Kafka producer
    _kafka_producer = KafkaProducer()
    await _kafka_producer.start()
    logger.info("Kafka producer started")

    # 2. Create dependencies for shipping handler
    uow_factory = get_uow_factory()
    retry_handler = get_retry_handler()
    notification_service = get_notification_service()
    shipping_use_case = ProcessShippingEventUseCase(
        uow_factory, retry_handler, notification_service
    )

    # 3. Define handler with injected dependencies
    async def handle_shipping_events_batch(data_list: list[dict]) -> None:
        if not data_list:
            return

        logger.info(f"Processing batch of {len(data_list)} shipping events")

        shipped_events = []
        cancelled_events = []

        for data in data_list:
            event_type = data.get("event_type")
            if event_type == "order.shipped":
                shipped_events.append(data)
            elif event_type == "order.cancelled":
                cancelled_events.append(data)
            else:
                logger.warning(f"Unknown event type in batch: {event_type}")

        for data in shipped_events:
            try:
                dto = OrderShippedEventDTO.from_dict(data)
                await shipping_use_case.process_shipped(dto)
            except Exception as e:
                logger.error(f"Error processing shipped event: {e}")

        for data in cancelled_events:
            try:
                dto = OrderCancelledEventDTO.from_dict(data)
                await shipping_use_case.process_cancelled(dto)
            except Exception as e:
                logger.error(f"Error processing cancelled event: {e}")

    # 4. Main consumer
    _kafka_consumer = KafkaConsumer(handler=handle_shipping_events_batch)
    await _kafka_consumer.start()
    logger.info("Main consumer started")

    _consumer_task = asyncio.create_task(_kafka_consumer.consume())
    logger.info("Main consumer loop started")

    # 5. Retry consumer
    _retry_consumer = RetryConsumer(producer=_kafka_producer)
    await _retry_consumer.start()
    logger.info("Retry consumer started")

    _retry_task = asyncio.create_task(_retry_consumer.consume())
    logger.info("Retry consumer loop started")

    # 6. Outbox worker
    uow_factory = get_uow_factory()
    process_outbox_use_case = ProcessOutboxUseCase(uow_factory, _kafka_producer)
    _outbox_worker = OutboxWorker(
        process_outbox_use_case=process_outbox_use_case,
        interval_seconds=5,
        batch_size=100,
    )
    await _outbox_worker.start()
    logger.info("Outbox worker started")

    yield

    # Shutdown
    logger.info("Shutting down...")

    if _outbox_worker:
        await _outbox_worker.stop()
        logger.info("Outbox worker stopped")

    if _retry_task:
        _retry_task.cancel()
        try:
            await _retry_task
        except asyncio.CancelledError:
            pass
        logger.info("Retry consumer loop stopped")

    if _retry_consumer:
        await _retry_consumer.stop()
        logger.info("Retry consumer stopped")

    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        logger.info("Main consumer loop stopped")

    if _kafka_consumer:
        await _kafka_consumer.stop()
        logger.info("Main consumer stopped")

    if _kafka_producer:
        await _kafka_producer.stop()
        logger.info("Kafka producer stopped")

    await engine.dispose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app = FastAPI(
        title=settings.SERVICE_NAME,
        version="1.0.0",
        description="Order Service with Clean Architecture",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": settings.SERVICE_NAME,
            "debug": settings.DEBUG,
        }

    return app
