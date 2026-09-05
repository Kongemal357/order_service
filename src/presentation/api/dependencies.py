from fastapi import Depends
from src.application.ports import CatalogClient, UnitOfWork
from src.application.ports.notification_client import NotificationClient
from src.application.ports.payment_client import PaymentClient
from src.application.services.notification_service import NotificationService
from src.application.usecases import CreateOrderUseCase, GetOrderUseCase
from src.application.usecases.process_outbox import ProcessOutboxUseCase
from src.application.usecases.process_payment_callback import ProcessPaymentCallbackUseCase
from src.application.usecases.process_shipping_event import ProcessShippingEventUseCase
from src.infrastructure.http.catalog_client import CatalogHTTPClient
from src.infrastructure.http.notification_client import NotificationHTTPClient
from src.infrastructure.http.payment_client import PaymentHTTPClient
from src.infrastructure.messaging.kafka_producer import KafkaProducer
from src.infrastructure.messaging.retry_consumer import RetryConsumer
from src.infrastructure.messaging.retry_handler import RetryHandler
from src.infrastructure.persistence.database import AsyncSessionLocal
from src.infrastructure.persistence.uow import SQLAlchemyUnitOfWork

# ============ Database Dependencies ============


def get_uow_factory() -> UnitOfWork:
    """
    Dependency for Unit of Work factory.

    Returns a factory that creates UoW instances.
    Usage: async with uow_factory() as uow:
    """
    return SQLAlchemyUnitOfWork(AsyncSessionLocal)


# ============ External Client Dependencies ============


def get_catalog_client() -> CatalogClient:
    """Dependency for Catalog Service client."""
    return CatalogHTTPClient()


def get_payment_client() -> PaymentClient:
    """Dependency for Payment Service client."""
    return PaymentHTTPClient()


def get_notification_client() -> NotificationClient:
    """Dependency for Notification Service client."""
    return NotificationHTTPClient()


def get_notification_service(
    client: NotificationClient = Depends(get_notification_client),
) -> NotificationService:
    """Dependency for Notification Service."""
    return NotificationService(client)


# ============ Kafka Dependencies ============


async def get_kafka_producer() -> KafkaProducer:
    """Dependency for Kafka producer."""
    producer = KafkaProducer()
    await producer.start()
    return producer


def get_retry_handler(
    producer: KafkaProducer = Depends(get_kafka_producer),
) -> RetryHandler:
    """Dependency for retry handler."""
    return RetryHandler(producer)


def get_retry_consumer(
    producer: KafkaProducer = Depends(get_kafka_producer),
) -> RetryConsumer:
    """Dependency for retry consumer."""
    return RetryConsumer(producer)


# ============ Use Case Dependencies ============


async def get_create_order_use_case(
    uow_factory: UnitOfWork = Depends(get_uow_factory),
    catalog_client: CatalogClient = Depends(get_catalog_client),
    payment_client: PaymentClient = Depends(get_payment_client),
    notification_service: NotificationService = Depends(get_notification_service),
) -> CreateOrderUseCase:
    """
    Dependency for create order use case.
    """
    return CreateOrderUseCase(uow_factory, catalog_client, payment_client, notification_service)


async def get_get_order_use_case(
    uow_factory: UnitOfWork = Depends(get_uow_factory),
) -> GetOrderUseCase:
    """
    Dependency for get order use case.
    """
    return GetOrderUseCase(uow_factory)


async def get_process_payment_callback_use_case(
    uow_factory: UnitOfWork = Depends(get_uow_factory),
    notification_service: NotificationService = Depends(get_notification_service),
) -> ProcessPaymentCallbackUseCase:
    """
    Dependency for process payment callback use case.
    """
    return ProcessPaymentCallbackUseCase(uow_factory, notification_service)


async def get_process_shipping_event_use_case(
    uow_factory: UnitOfWork = Depends(get_uow_factory),
    retry_handler: RetryHandler = Depends(get_retry_handler),
    notification_service: NotificationService = Depends(get_notification_service),
) -> ProcessShippingEventUseCase:
    """
    Dependency for process shipping event use case.
    """
    return ProcessShippingEventUseCase(uow_factory, retry_handler, notification_service)


async def get_process_outbox_use_case(
    uow_factory: UnitOfWork = Depends(get_uow_factory),
    kafka_producer: KafkaProducer = Depends(get_kafka_producer),
) -> ProcessOutboxUseCase:
    """
    Dependency for process outbox use case.
    """
    return ProcessOutboxUseCase(uow_factory, kafka_producer)
